"""Handler for database operations related to embedding models."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.embedding_model import (
    EmbeddingModelCreate,
    EmbeddingModelTable,
)


def create(session: Session, embedding_model: EmbeddingModelCreate) -> EmbeddingModelTable:
    """Create a new EmbeddingModel in the database."""
    db_embedding_model = EmbeddingModelTable.model_validate(embedding_model)
    session.add(db_embedding_model)
    session.commit()
    session.refresh(db_embedding_model)
    return db_embedding_model


def get_or_create(session: Session, embedding_model: EmbeddingModelCreate) -> EmbeddingModelTable:
    """Retrieve an existing EmbeddingModel by hash or create a new one if it does not exist."""
    db_model = get_by_model_hash_deprecated(
        session=session,
        collection_id=embedding_model.collection_id,
        embedding_model_hash=embedding_model.embedding_model_hash,
    )
    if db_model is None:
        return create(session=session, embedding_model=embedding_model)

    # Validate that the existing model matches the provided data.
    if (
        db_model.name != embedding_model.name
        or db_model.parameter_count_in_mb != embedding_model.parameter_count_in_mb
        or db_model.embedding_dimension != embedding_model.embedding_dimension
    ):
        raise ValueError(
            "An embedding model with the same hash but different parameters already exists."
        )
    return db_model


def get_all_by_collection_id(session: Session, collection_id: UUID) -> list[EmbeddingModelTable]:
    """Retrieve all embedding models."""
    embedding_models = session.exec(
        select(EmbeddingModelTable)
        .where(EmbeddingModelTable.collection_id == collection_id)
        .order_by(col(EmbeddingModelTable.created_at).asc())
    ).all()
    return list(embedding_models)


def get_by_id(session: Session, embedding_model_id: UUID) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by ID."""
    return session.exec(
        select(EmbeddingModelTable).where(
            EmbeddingModelTable.embedding_model_id == embedding_model_id
        )
    ).one_or_none()


# TODO(Michal, 08/2026): Remove once the write path deduplicates per dataset and the readers
# no longer resolve embedding models by collection.
def get_by_model_hash_deprecated(
    session: Session, collection_id: UUID, embedding_model_hash: str
) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by hash and collection.

    Kept for the write path, which still deduplicates per collection until the readers move
    to dataset scope. Prefer :func:`get_by_model_hash` for new reads.
    """
    query = select(EmbeddingModelTable).where(
        EmbeddingModelTable.embedding_model_hash == embedding_model_hash
    )
    query = query.where(EmbeddingModelTable.collection_id == collection_id)
    return session.exec(query).one_or_none()


def get_by_model_hash(
    session: Session, dataset_id: UUID, embedding_model_hash: str
) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by hash within a dataset.

    The same hash can appear once per collection because the write path still deduplicates
    per collection (see :func:`get_by_model_hash_deprecated`), so a dataset can hold
    duplicates. The oldest match is returned so they resolve deterministically to the
    canonical row.

    Args:
        session: The database session.
        dataset_id: The dataset in which to search for the embedding model.
        embedding_model_hash: The hash identifying the embedding model.

    Returns:
        The oldest matching embedding model, or None if no matching model exists.
    """
    query = (
        select(EmbeddingModelTable)
        .where(EmbeddingModelTable.embedding_model_hash == embedding_model_hash)
        .where(EmbeddingModelTable.dataset_id == dataset_id)
        .order_by(
            col(EmbeddingModelTable.created_at).asc(),
            col(EmbeddingModelTable.embedding_model_id).asc(),
        )
    )
    return session.exec(query).first()
