"""Handler for database operations related to sample embeddings."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlalchemy import String, cast, func
from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_embedding import (
    SampleEmbeddingCreate,
    SampleEmbeddingTable,
)


def create(session: Session, sample_embedding: SampleEmbeddingCreate) -> SampleEmbeddingTable:
    """Create a new SampleEmbedding in the database."""
    db_sample_embedding = SampleEmbeddingTable.model_validate(sample_embedding)
    session.add(db_sample_embedding)
    session.commit()
    session.refresh(db_sample_embedding)
    return db_sample_embedding


def create_many(session: Session, sample_embeddings: list[SampleEmbeddingCreate]) -> None:
    """Create many sample embeddings in a single database commit."""
    db_sample_embeddings = [SampleEmbeddingTable.model_validate(e) for e in sample_embeddings]
    session.bulk_save_objects(db_sample_embeddings)
    session.commit()


def get_by_sample_ids(
    session: Session,
    sample_ids: list[UUID],
    embedding_model_id: UUID,
) -> list[SampleEmbeddingTable]:
    """Get sample embeddings for the specified sample IDs.

    Output order matches the input order.

    Args:
        session: The database session.
        sample_ids: List of sample IDs to get embeddings for.
        embedding_model_id: The embedding model ID to filter by.

    Returns:
        List of sample embeddings associated with the provided IDs.
    """
    string_ids = [str(id_) for id_ in sample_ids]
    results = list(
        session.exec(
            select(SampleEmbeddingTable)
            .where(cast(SampleEmbeddingTable.sample_id, String).in_(string_ids))
            .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        ).all()
    )
    # Return embeddings in the same order as the input IDs
    embedding_map = {embedding.sample_id: embedding for embedding in results}
    return [embedding_map[id_] for id_ in sample_ids if id_ in embedding_map]


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
    embedding_model_id: UUID,
) -> list[SampleEmbeddingTable]:
    """Get all sample embeddings for samples in a specific dataset.

    Args:
        session: The database session.
        dataset_id: The dataset ID to filter by.
        embedding_model_id: The embedding model ID to filter by.

    Returns:
        List of sample embeddings associated with the dataset.
    """
    query = (
        select(SampleEmbeddingTable)
        .join(SampleTable)
        .where(SampleEmbeddingTable.sample_id == SampleTable.sample_id)
        .where(SampleTable.dataset_id == dataset_id)
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
        .order_by(col(SampleTable.file_path_abs).asc())
    )
    return list(session.exec(query).all())


def get_hash_by_sample_ids(
    session: Session,
    sample_ids_ordered: list[UUID],
    embedding_model_id: UUID,
) -> tuple[str, list[UUID]]:
    """Return a combined hash and the ordered sample IDs with stored embeddings.

    Args:
        session: Database session.
        sample_ids_ordered: Sample IDs to consider, order defines deterministic hash.
        embedding_model_id: Embedding model identifier.

    Returns:
        Tuple of (combined hash, ordered sample IDs that have stored embeddings).
    """
    if not sample_ids_ordered:
        return "empty", []

    rows = session.exec(
        select(
            SampleEmbeddingTable.sample_id,
            func.hash(SampleEmbeddingTable.embedding).label("hash_column"),
        )
        .where(col(SampleEmbeddingTable.sample_id).in_(set(sample_ids_ordered)))
        .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
    ).all()

    # Mypy does not get that 'hash_column' is an attribute of the returned rows
    sample_id_to_hash = {row.sample_id: row.hash_column for row in rows}  # type: ignore[attr-defined]
    sample_ids_of_samples_with_embeddings = [
        sample_id for sample_id in sample_ids_ordered if sample_id in sample_id_to_hash
    ]
    hashes_ordered = [sample_id_to_hash[sample_id] for sample_id in sample_ids_of_samples_with_embeddings]

    hasher = hashlib.sha256()
    hasher.update("".join(str(h) for h in hashes_ordered).encode("utf-8"))
    return hasher.hexdigest(), sample_ids_of_samples_with_embeddings
