"""Handler for database operations related to embedding models."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.embedding_model import (
    EmbeddingModelCreate,
    EmbeddingModelTable,
)
from lightly_studio.resolvers import default_embedding_space_resolver


def create(session: Session, embedding_model: EmbeddingModelCreate) -> EmbeddingModelTable:
    """Create a new EmbeddingModel in the database."""
    db_embedding_model = EmbeddingModelTable.model_validate(embedding_model)
    session.add(db_embedding_model)
    session.commit()
    session.refresh(db_embedding_model)
    return db_embedding_model


def get_or_create(session: Session, embedding_model: EmbeddingModelCreate) -> EmbeddingModelTable:
    """Retrieve an existing EmbeddingModel by hash or create a new one if it does not exist."""
    db_model = get_by_model_hash(
        session=session,
        dataset_id=embedding_model.dataset_id,
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


def get_default_by_collection_id(
    session: Session, collection_id: UUID
) -> EmbeddingModelTable | None:
    """Retrieve the collection's default embedding model, or None if it has none.

    A collection is associated with a single model through ``default_embedding_space``.
    """
    embedding_model_id = default_embedding_space_resolver.get_by_collection_id(
        session=session, collection_id=collection_id
    )
    if embedding_model_id is None:
        return None
    return get_by_id(session=session, embedding_model_id=embedding_model_id)


def get_by_id(session: Session, embedding_model_id: UUID) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by ID."""
    return session.exec(
        select(EmbeddingModelTable).where(
            EmbeddingModelTable.embedding_model_id == embedding_model_id
        )
    ).one_or_none()


def get_by_model_hash(
    session: Session, dataset_id: UUID, embedding_model_hash: str
) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by hash within a dataset.

    The write path deduplicates per ``(dataset_id, embedding_model_hash)``, but no unique
    constraint enforces it yet (it lands with the ``collection_id`` drop). The oldest match
    is returned so legacy duplicates resolve deterministically to the canonical row.
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


def get_by_name(
    session: Session, collection_id: UUID, embedding_model_name: str | None
) -> EmbeddingModelTable:
    """Resolve the collection's default embedding model, optionally checking its name.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        embedding_model_name: The expected name of the default model. If None, the default
            is returned as is. If set, the default is returned only when its name matches.

    Returns:
        The collection's default embedding model.

    Raises:
        ValueError: If the collection has no default model, or its name does not match
            ``embedding_model_name``.
    """
    embedding_model = get_default_by_collection_id(session=session, collection_id=collection_id)

    if embedding_model_name is None:
        if embedding_model is None:
            raise ValueError("The collection has no default embedding model.")
        return embedding_model

    if embedding_model is None or embedding_model.name != embedding_model_name:
        raise ValueError(f"Embedding model with name `{embedding_model_name}` not found.")

    return embedding_model


def delete(session: Session, embedding_model_id: UUID) -> bool:
    """Delete an embedding model."""
    embedding_model = get_by_id(session=session, embedding_model_id=embedding_model_id)
    if not embedding_model:
        return False

    session.delete(embedding_model)
    session.commit()
    return True
