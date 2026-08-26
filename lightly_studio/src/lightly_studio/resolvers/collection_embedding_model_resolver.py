"""Handler for database operations related to a collection's default embedding space."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable


def set_default(
    session: Session, collection_id: UUID, embedding_model_id: UUID
) -> CollectionEmbeddingModelTable:
    """Set (or replace) the default embedding space of a collection.

    A collection has at most one default, so an existing row is updated in place rather
    than inserted a second time.

    Args:
        session: The database session.
        collection_id: The collection whose default is set.
        embedding_model_id: The embedding model to record as the default.

    Returns:
        The persisted default embedding space row.
    """
    default = _get_by_collection_id(session=session, collection_id=collection_id)
    if default is None:
        default = CollectionEmbeddingModelTable(
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            is_default=True,
        )
    else:
        default.embedding_model_id = embedding_model_id

    session.add(default)
    session.commit()
    session.refresh(default)
    return default


def get_by_collection_id(session: Session, collection_id: UUID) -> UUID | None:
    """Return the collection's default embedding model id, or None if it has none."""
    default = _get_by_collection_id(session=session, collection_id=collection_id)
    return None if default is None else default.embedding_model_id


def delete_by_collection_id(session: Session, collection_id: UUID) -> bool:
    """Delete the collection's default embedding space row.

    Returns:
        True if a row was deleted, False if the collection had no default.
    """
    default = _get_by_collection_id(session=session, collection_id=collection_id)
    if default is None:
        return False

    session.delete(default)
    session.commit()
    return True


def _get_by_collection_id(
    session: Session, collection_id: UUID
) -> CollectionEmbeddingModelTable | None:
    """Return the collection's default embedding space row, or None if it has none."""
    return session.exec(
        select(CollectionEmbeddingModelTable).where(
            CollectionEmbeddingModelTable.collection_id == collection_id
        )
    ).one_or_none()
