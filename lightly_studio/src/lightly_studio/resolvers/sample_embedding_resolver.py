"""Handler for database operations related to sample embeddings."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator, Mapping, Sequence
from typing import Any, NamedTuple
from uuid import UUID

from sqlalchemy import ARRAY, BindParameter, Float, bindparam, func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.database import db_insert, db_vector
from lightly_studio.database.db_manager import DatabaseBackend
from lightly_studio.database.db_vector import Embedding
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
    SampleEmbeddingTable,
)
from lightly_studio.resolvers import embedding_model_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.utils import batching


class SampleEmbeddingRow(NamedTuple):
    """A sample id paired with its embedding vector.

    Lightweight read result for ``get_by_sample_ids``: only the ``sample_id`` and
    ``embedding`` columns are loaded, never a full ``SampleEmbeddingTable`` object.
    """

    sample_id: UUID
    embedding: Embedding


class SampleProjectionRow(NamedTuple):
    """A sample id paired with the projections of its embedding onto two directions."""

    sample_id: UUID
    x: float
    y: float


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

    Skips an embedding whose sample and model already have an embedding, for example one
    that a concurrent caller stored first.

    Args:
        session: The database session.
        sample_embeddings: The embeddings to insert.
        commit: Whether to commit. Pass ``False`` to insert as part of a larger
            transaction that the caller commits, so multiple calls stay atomic.
    """
    rows = [SampleEmbeddingTable.model_validate(e).model_dump() for e in sample_embeddings]
    db_insert.insert_ignoring_conflicts(session=session, table=SampleEmbeddingTable, rows=rows)
    if commit:
        session.commit()


# get_by_sample_ids and get_all_by_collection_id differ only by their input (which samples
# to load), not by backend. Each picks the backend and then uses a shared
# backend read path:
# Postgres: bypassing SQLAlchemy to read binary directly -> around 10x faster
# DuckDB: using a normal SQLAlchemy session.exec
#
#                            PostgreSQL                    DuckDB
#   get_by_sample_ids        "= ANY" SQL                   batched IN
#   get_all_by_collection_id compiled SELECT               session.exec
#   backend read primitive   _read_embedding_rows_binary   ---


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
    results: list[SampleEmbeddingRow]
    if session.get_bind().dialect.name == DatabaseBackend.POSTGRESQL.value:
        # A single ``sample_id = ANY(%s)`` array param stays under Postgres' bind-parameter
        # limit, so no batching is needed.
        query = (
            "SELECT sample_id, embedding FROM sample_embedding "
            "WHERE embedding_model_id = %s AND sample_id = ANY(%s)"
        )
        results = _read_embedding_rows_binary(session, query, (embedding_model_id, sample_ids))
    else:
        # DuckDB: batch the ids to stay under the statement's parameter limit.
        results = []
        for batch in batching.batched(items=sample_ids):
            statement = (
                select(SampleEmbeddingTable.sample_id, col(SampleEmbeddingTable.embedding))
                .where(col(SampleEmbeddingTable.sample_id).in_(batch))
                .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
            )
            results.extend(
                SampleEmbeddingRow(sample_id=sample_id, embedding=embedding)
                for sample_id, embedding in session.exec(statement).all()
            )
    # Return embeddings in the same order as the input IDs
    embedding_map = {embedding.sample_id: embedding for embedding in results}
    return [embedding_map[id_] for id_ in sample_ids if id_ in embedding_map]


def get_all_by_collection_id(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    filters: SampleFilter | None = None,
) -> list[SampleEmbeddingRow]:
    """Get all sample embeddings for samples in a specific collection.

    On PostgreSQL the embeddings are read with a binary psycopg cursor (decoded via
    ``np.frombuffer``); DuckDB returns them as arrays natively and uses the regular query
    path. Output is ordered by sample creation time, with ``sample_id`` as a tiebreaker
    for a deterministic order. Callers do not need to distinguish between backends.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        embedding_model_id: The embedding model ID to filter by.
        filters: Filters to apply to the samples.

    Returns:
        Embeddings for the collection, ordered by sample creation time.
    """
    statement = (
        select(SampleEmbeddingTable.sample_id, col(SampleEmbeddingTable.embedding))
        .join(SampleTable, col(SampleEmbeddingTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        .order_by(col(SampleTable.created_at).asc(), col(SampleEmbeddingTable.sample_id).asc())
    )
    if filters:
        statement = filters.apply(statement)
    if session.get_bind().dialect.name == DatabaseBackend.POSTGRESQL.value:
        # Compile to SQL + params and read it on the binary cursor.
        compiled = statement.compile(
            dialect=session.get_bind().dialect,
            compile_kwargs={"render_postcompile": True},
        )
        return _read_embedding_rows_binary(session, str(compiled), compiled.params)
    streamed = statement.execution_options(yield_per=batching.DEFAULT_BATCH_SIZE)
    return [
        SampleEmbeddingRow(sample_id=sample_id, embedding=embedding)
        for sample_id, embedding in session.exec(streamed)
    ]


def get_projections_by_collection_id(
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    direction_x: Sequence[float],
    direction_y: Sequence[float],
) -> Iterator[SampleProjectionRow]:
    """Get the projections of the sample embeddings of a collection onto two directions.

    D is the embedding dimension. The x and y values of a sample are the dot products of its
    embedding with ``direction_x`` and ``direction_y``. The database computes them, so the
    embeddings are not loaded into Python. The rows stream from the database in batches, so
    keep the session open until the iteration ends.

    Args:
        session: The database session.
        collection_id: The collection ID to filter by.
        embedding_model_id: The embedding model ID to filter by.
        direction_x: The X direction of shape (D,).
        direction_y: The Y direction of shape (D,).

    Returns:
        The projections of the samples with an embedding, ordered by sample creation time,
        with the sample ID as a tiebreaker.

    Raises:
        ValueError: If the embedding model does not exist, or if a direction does not have
            the embedding dimension.
    """
    embedding_model = embedding_model_resolver.get_by_id(
        session=session, embedding_model_id=embedding_model_id
    )
    if embedding_model is None:
        raise ValueError(f"Embedding model {embedding_model_id} not found.")
    dimension = embedding_model.embedding_dimension
    if dimension != len(direction_x) or dimension != len(direction_y):
        raise ValueError(
            f"The axis directions must have the embedding dimension {dimension}, "
            f"got {len(direction_x)} and {len(direction_y)}."
        )

    embeddings = (
        select(
            SampleEmbeddingTable.sample_id,
            col(SampleTable.created_at),
            db_vector.loaded_vector(col(SampleEmbeddingTable.embedding), dimension).label(
                "embedding"
            ),
        )
        .join(SampleTable, col(SampleEmbeddingTable.sample_id) == col(SampleTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        # OFFSET 0 keeps PostgreSQL from merging the subquery into the outer query. Then both
        # dot products use the same loaded vector, and each vector loads only once.
        .offset(0)
        .subquery()
    )
    statement = select(
        embeddings.c.sample_id,
        db_vector.inner_product(embeddings.c.embedding, _direction_param(direction=direction_x)),
        db_vector.inner_product(embeddings.c.embedding, _direction_param(direction=direction_y)),
    ).order_by(embeddings.c.created_at.asc(), embeddings.c.sample_id.asc())
    # A function with yield runs only when the iteration starts. The checks above are in this
    # function, so that they run at the call.
    return _stream_projections(session=session, statement=statement)


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


def _read_embedding_rows_binary(
    session: Session, sql: str, params: Sequence[Any] | Mapping[str, Any]
) -> list[SampleEmbeddingRow]:
    """Run a ``(sample_id, embedding)`` SELECT on a binary psycopg cursor (PostgreSQL).

    Reading the vectors in pgvector's binary format (via ``np.frombuffer``) is far faster
    than parsing them from text for each row. ``params`` is a tuple for ``%s`` placeholders
    or a dict for ``%(name)s``.
    """
    # Push any pending writes in this session to the database first so the cursor below —
    # which bypasses SQLAlchemy's result handling — sees them (it shares the session's
    # connection and transaction). The normal query path does this automatically.
    session.flush()
    connection = db_vector.get_pgvector_connection(session)
    with connection.cursor(binary=True) as cursor:
        cursor.execute(sql, params)
        return [
            SampleEmbeddingRow(sample_id=sample_id, embedding=embedding)
            for sample_id, embedding in cursor
        ]


def _stream_projections(
    session: Session, statement: Select[tuple[UUID, float, float]]
) -> Iterator[SampleProjectionRow]:
    """Yield the ``(sample_id, x, y)`` rows of a statement, fetched in batches."""
    streamed = statement.execution_options(yield_per=batching.DEFAULT_BATCH_SIZE)
    for sample_id, x, y in session.exec(streamed):
        yield SampleProjectionRow(sample_id=sample_id, x=x, y=y)


def _direction_param(direction: Sequence[float]) -> BindParameter[Sequence[float]]:
    """Return a bound parameter with the values of a direction vector."""
    return bindparam(
        None, value=[float(value) for value in direction], type_=ARRAY(Float), unique=True
    )
