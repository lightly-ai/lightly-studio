"""Handler for database operations related to sample embeddings."""

from __future__ import annotations

import hashlib
from typing import NamedTuple
from uuid import UUID

import pgvector.psycopg
from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.database import db_vector
from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
    SampleEmbeddingTable,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.utils import batching


class SampleEmbeddingRow(NamedTuple):
    """A sample id paired with its embedding vector.

    Lightweight read result for ``get_by_sample_ids``: only the ``sample_id`` and
    ``embedding`` columns are loaded, never a full ``SampleEmbeddingTable`` object.
    """

    sample_id: UUID
    embedding: Embedding


def create(session: Session, sample_embedding: SampleEmbeddingCreate) -> SampleEmbeddingTable:
    """Create a new SampleEmbedding in the database."""
    db_sample_embedding = SampleEmbeddingTable.model_validate(sample_embedding)
    session.add(db_sample_embedding)
    session.commit()
    session.refresh(db_sample_embedding)
    return db_sample_embedding


def create_many(
    session: Session, sample_embeddings: list[SampleEmbeddingCreate], commit: bool = True
) -> None:
    """Create many sample embeddings.

    Args:
        session: The database session.
        sample_embeddings: The embeddings to insert.
        commit: Whether to commit. Pass ``False`` to insert as part of a larger
            transaction that the caller commits, so multiple calls stay atomic.
    """
    db_sample_embeddings = [SampleEmbeddingTable.model_validate(e) for e in sample_embeddings]
    session.bulk_save_objects(db_sample_embeddings)
    if commit:
        session.commit()


def get_by_sample_ids(
    session: Session,
    sample_ids: list[UUID],
    embedding_model_id: UUID,
) -> list[SampleEmbeddingRow]:
    """Get sample embeddings for the specified sample IDs.

    Output order matches the input order.

    Args:
        session: The database session.
        sample_ids: List of sample IDs to get embeddings for.
        embedding_model_id: The embedding model ID to filter by.

    Returns:
        List of sample embeddings associated with the provided IDs.
    """
    if not sample_ids:
        return []
    if session.get_bind().dialect.name == "postgresql":
        results = _get_by_sample_ids_postgres(
            session=session, sample_ids=sample_ids, embedding_model_id=embedding_model_id
        )
    else:
        results = _get_by_sample_ids_duckdb(
            session=session, sample_ids=sample_ids, embedding_model_id=embedding_model_id
        )
    # Return embeddings in the same order as the input IDs
    embedding_map = {embedding.sample_id: embedding for embedding in results}
    return [embedding_map[id_] for id_ in sample_ids if id_ in embedding_map]


def _get_by_sample_ids_postgres(
    session: Session,
    sample_ids: list[UUID],
    embedding_model_id: UUID,
) -> list[SampleEmbeddingRow]:
    """Load embeddings with a binary psycopg cursor (PostgreSQL only).

    Reading the vectors in pgvector's binary format (via ``np.frombuffer``) is far
    faster than parsing them from text for each row.
    """
    # Push any pending writes in this session to the database first so the cursor below
    # sees them (it shares the session's connection and transaction). The normal query
    # path does this automatically.
    session.flush()
    connection = session.connection().connection
    driver_connection = connection.driver_connection
    if driver_connection is None:  # pragma: no cover - a live session always has one
        raise RuntimeError("PostgreSQL session has no underlying psycopg connection.")
    if not connection.info.get("pgvector_registered"):
        # Register pgvector once per connection so psycopg decodes ``vector`` columns
        # from binary instead of parsing them from text.
        pgvector.psycopg.register_vector(driver_connection)
        connection.info["pgvector_registered"] = True
    query = (
        "SELECT sample_id, embedding FROM sample_embedding "
        "WHERE embedding_model_id = %s AND sample_id = ANY(%s)"
    )
    with driver_connection.cursor(binary=True) as cursor:
        cursor.execute(query, (embedding_model_id, sample_ids))
        return [
            SampleEmbeddingRow(sample_id=sample_id, embedding=embedding)
            for sample_id, embedding in cursor
        ]


def _get_by_sample_ids_duckdb(
    session: Session,
    sample_ids: list[UUID],
    embedding_model_id: UUID,
) -> list[SampleEmbeddingRow]:
    """Load embeddings via the SQLAlchemy query path (DuckDB).

    DuckDB returns the vectors as arrays natively, so selecting just ``sample_id`` and
    ``embedding`` avoids creating full ``SampleEmbeddingTable`` objects. IDs are batched
    to stay under the database's parameter limit.
    """
    rows: list[SampleEmbeddingRow] = []
    for batch in batching.batched(items=sample_ids):
        results = session.exec(
            select(SampleEmbeddingTable.sample_id, col(SampleEmbeddingTable.embedding))
            .where(col(SampleEmbeddingTable.sample_id).in_(batch))
            .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        ).all()
        rows.extend(
            SampleEmbeddingRow(sample_id=sample_id, embedding=embedding)
            for sample_id, embedding in results
        )
    return rows


def get_all_by_collection_id(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    filters: SampleFilter | None = None,
) -> list[SampleEmbeddingTable]:
    """Get all sample embeddings for samples in a specific collection.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        embedding_model_id: The embedding model ID to filter by.
        filters: Filters to apply to the samples.

    Returns:
        List of sample embeddings associated with the collection.
    """
    query = (
        select(SampleEmbeddingTable)
        .join(SampleTable, col(SampleEmbeddingTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        .order_by(col(SampleTable.created_at).asc())
    )
    if filters:
        query = filters.apply(query)
    # Fetch in chunks so list[float] rows are converted to numpy and freed per batch.
    query = query.execution_options(yield_per=batching.DEFAULT_BATCH_SIZE)
    return list(session.exec(query).all())


def get_hash_by_collection_id(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> tuple[str, list[UUID]]:
    """Return a combined hash and ordered sample IDs with embeddings for a collection.

    The cache key is derived from the first dimension of each embedding vector,
    which is database-agnostic (works with both DuckDB and PostgreSQL).

    Args:
        session: Database session.
        collection_id: The collection ID to consider.
        embedding_model_id: Embedding model identifier.

    Returns:
        Tuple of (combined hash, ordered sample IDs that have stored embeddings).
    """
    first_dim_col = db_vector.vector_element(SampleEmbeddingTable.embedding, 1).label("first_dim")

    rows = session.exec(
        select(
            SampleEmbeddingTable.sample_id,
            first_dim_col,
        )
        .join(SampleTable, col(SampleEmbeddingTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        .order_by(col(SampleEmbeddingTable.sample_id).asc())
    ).all()

    sample_ids: list[UUID] = []
    hasher = hashlib.sha256()

    for row in rows:
        sample_ids.append(row.sample_id)  # type: ignore[attr-defined]
        hasher.update(str(row.first_dim).encode("utf-8"))  # type: ignore[attr-defined]

    if not sample_ids:
        return "empty", []
    return hasher.hexdigest(), sample_ids


def get_embedding_count(session: Session, collection_id: UUID, embedding_model_id: UUID) -> int:
    """Get the number of sample embeddings for samples in a specific collection.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        embedding_model_id: The embedding model ID to filter by.

    Returns:
        The number of sample embeddings associated with the collection.
    """
    query = (
        select(func.count(col(SampleEmbeddingTable.sample_id)))
        .join(SampleTable, col(SampleEmbeddingTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
    )
    return session.exec(query).one()
