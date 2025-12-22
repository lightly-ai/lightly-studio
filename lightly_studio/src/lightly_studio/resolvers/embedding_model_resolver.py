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
    db_model = get_by_model_hash(
        session=session, embedding_model_hash=embedding_model.embedding_model_hash
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


def get_by_model_hash(session: Session, embedding_model_hash: str) -> EmbeddingModelTable | None:
    """Retrieve a single embedding model by hash."""
    return session.exec(
        select(EmbeddingModelTable).where(
            EmbeddingModelTable.embedding_model_hash == embedding_model_hash
        )
    ).one_or_none()


def get_by_name(
    session: Session, collection_id: UUID, embedding_model_name: str | None
) -> EmbeddingModelTable:
    """Helper function to resolve the embedding model name to its ID.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        embedding_model_name: The name of the embedding model.
            If None, expects the collection to have exactly one embedding model and
            returns it. Otherwise raises a ValueError.
            If set, expects the collection to have an embedding model with the given name.
            Otherwise raises a ValueError.

    Returns:
        The embedding model with the given name.
    """
    embedding_models = get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
    )

    if embedding_model_name is None:
        if len(embedding_models) != 1:
            raise ValueError(
                f"Expected exactly one embedding model, "
                f"but found {len(embedding_models)} with names "
                f"{[model.name for model in embedding_models]}."
            )
        return embedding_models[0]

    embedding_model_with_name = next(
        (model for model in embedding_models if model.name == embedding_model_name), None
    )
    if embedding_model_with_name is None:
        raise ValueError(f"Embedding model with name `{embedding_model_name}` not found.")

    return embedding_model_with_name


def delete(session: Session, embedding_model_id: UUID) -> bool:
    """Delete an embedding model."""
    embedding_model = get_by_id(session=session, embedding_model_id=embedding_model_id)
    if not embedding_model:
        return False

    session.delete(embedding_model)
    session.commit()
    return True
