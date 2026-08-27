"""Handler for database operations related to a collection's default embedding space."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable


def set_default(
    session: Session, collection_id: UUID, embedding_model_id: UUID
) -> CollectionEmbeddingModelTable:
    """Set the default embedding model of a collection.

    A collection may link several embedding models but has at most one default. The
    current default (if any) is cleared and the target model is flagged instead. The
    target keeps its existing link row when it already has one, so the composite primary
    key is never mutated.

    Args:
        session: The database session.
        collection_id: The collection whose default is set.
        embedding_model_id: The embedding model to record as the default.

    Returns:
        The persisted default embedding model row.
    """
    current_default = _get_by_collection_id(session=session, collection_id=collection_id)
    if current_default is not None and current_default.embedding_model_id == embedding_model_id:
        return current_default

    # Clear the old default first so the one-default-per-collection unique index (Postgres)
    # never sees two defaults at once.
    if current_default is not None:
        current_default.is_default = False
        session.add(current_default)
        session.flush()

    target = session.get(CollectionEmbeddingModelTable, (collection_id, embedding_model_id))
    if target is None:
        target = CollectionEmbeddingModelTable(
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            is_default=True,
        )
    else:
        target.is_default = True

    session.add(target)
    session.commit()
    session.refresh(target)
    return target


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
    """Return the collection's default embedding model row, or None if it has none."""
    return session.exec(
        select(CollectionEmbeddingModelTable).where(
            CollectionEmbeddingModelTable.collection_id == collection_id,
            col(CollectionEmbeddingModelTable.is_default).is_(True),
        )
    ).one_or_none()
