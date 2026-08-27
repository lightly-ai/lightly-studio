"""Handler for database operations on the collection-to-embedding-model link table.

Each row links one embedding model to one collection, with an ``is_default`` flag marking
at most one of a collection's models as its default. Linking a model and choosing the
default are separate operations: ``get_or_create`` links, ``set_default`` flips the flag.
"""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable


def get_or_create(
    session: Session, collection_id: UUID, embedding_model_id: UUID
) -> CollectionEmbeddingModelTable:
    """Link an embedding model to a collection, returning the existing or new link row.

    Idempotent: linking a model that is already linked returns its current row and never
    touches ``is_default``. The composite primary key makes the link naturally unique, so
    no separate "fail if exists" insert is needed. Whether a linked model is the
    collection's default is a separate concern owned by ``set_default``.

    Args:
        session: The database session.
        collection_id: The collection to link the model to.
        embedding_model_id: The embedding model to link.

    Returns:
        The persisted link row.
    """
    link = session.get(CollectionEmbeddingModelTable, (collection_id, embedding_model_id))
    if link is not None:
        return link

    link = CollectionEmbeddingModelTable(
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def set_default(
    session: Session, collection_id: UUID, embedding_model_id: UUID
) -> CollectionEmbeddingModelTable:
    """Make an already-linked embedding model the collection's default.

    A collection has at most one default. The current default (if any) is cleared and the
    target model is flagged instead. The target must already be linked via
    ``get_or_create``; an unlinked model reaching here is a caller bug and raises.

    Args:
        session: The database session.
        collection_id: The collection whose default is set.
        embedding_model_id: The already-linked embedding model to flag as the default.

    Returns:
        The persisted default embedding model row.

    Raises:
        ValueError: If the model is not linked to the collection.
    """
    target = session.get(CollectionEmbeddingModelTable, (collection_id, embedding_model_id))
    if target is None:
        raise ValueError(
            f"Embedding model {embedding_model_id} is not linked to collection {collection_id}."
        )
    if target.is_default:
        return target

    # Clear the old default first so the one-default-per-collection unique index (Postgres)
    # never sees two defaults at once.
    current_default = _get_default_by_collection_id(session=session, collection_id=collection_id)
    if current_default is not None:
        current_default.is_default = False
        session.add(current_default)
        session.flush()

    target.is_default = True
    session.add(target)
    session.commit()
    session.refresh(target)
    return target


def get_default_by_collection_id(session: Session, collection_id: UUID) -> UUID | None:
    """Return the collection's default embedding model id, or None if it has none."""
    default = _get_default_by_collection_id(session=session, collection_id=collection_id)
    return None if default is None else default.embedding_model_id


def get_all_by_collection_id(session: Session, collection_id: UUID) -> list[UUID]:
    """Return the ids of all embedding models linked to the collection."""
    return list(
        session.exec(
            select(CollectionEmbeddingModelTable.embedding_model_id).where(
                CollectionEmbeddingModelTable.collection_id == collection_id
            )
        ).all()
    )


def _get_default_by_collection_id(
    session: Session, collection_id: UUID
) -> CollectionEmbeddingModelTable | None:
    """Return the collection's default embedding model row, or None if it has none."""
    return session.exec(
        select(CollectionEmbeddingModelTable).where(
            CollectionEmbeddingModelTable.collection_id == collection_id,
            col(CollectionEmbeddingModelTable.is_default).is_(True),
        )
    ).one_or_none()
