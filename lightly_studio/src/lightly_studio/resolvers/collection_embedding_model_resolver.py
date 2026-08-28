"""Handler for database operations on the collection-to-embedding-model link table.

Each row links one embedding model to one collection, with an ``is_default`` flag marking
at most one of a collection's models as its default. Linking a model and choosing the
default are separate operations: ``get_or_create`` links, ``set_default`` flips the flag.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import exists
from sqlmodel import Session, col, select

from lightly_studio.models.collection_embedding_model import CollectionEmbeddingModelTable
from lightly_studio.models.embedding_model import EmbeddingModelTable


def get_or_add_collection_model(
    session: Session, collection_id: UUID, embedding_model_id: UUID
) -> CollectionEmbeddingModelTable:
    """Link an embedding model to a collection, returning the existing or new link row.

    If the link does not exist it is created as non-default.

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


def has_default_by_collection_id(session: Session, collection_id: UUID) -> bool:
    """Return whether the collection has a default embedding model."""
    stmt = select(
        exists().where(
            col(CollectionEmbeddingModelTable.collection_id) == collection_id,
            col(CollectionEmbeddingModelTable.is_default).is_(True),
        )
    )
    return session.exec(stmt).one()


def get_all_by_collection_id(session: Session, collection_id: UUID) -> list[UUID]:
    """Return the ids of all embedding models linked to the collection."""
    return list(
        session.exec(
            select(CollectionEmbeddingModelTable.embedding_model_id).where(
                CollectionEmbeddingModelTable.collection_id == collection_id
            )
        ).all()
    )


def get_model_by_name(
    session: Session, collection_id: UUID, embedding_model_name: str | None
) -> UUID:
    """Resolve the id of one of a collection's embedding models by name.

    Args:
        session: The database session.
        collection_id: The ID of the collection.
        embedding_model_name: The name of the embedding model.
            If None, the collection's default embedding model id is returned. Raises a
            ValueError if the collection has no default.
            If set, expects the collection to have an embedding model with the given name.
            Otherwise raises a ValueError.

    Returns:
        The id of the embedding model with the given name, or of the default when no name
        is given.

    Raises:
        ValueError: If the name is None and the collection has no default model, or if no
            linked model has the given name.
    """
    if embedding_model_name is None:
        default_id = get_default_by_collection_id(session=session, collection_id=collection_id)
        if default_id is None:
            raise ValueError(f"Collection {collection_id} has no default embedding model.")
        return default_id

    embedding_model_id = session.exec(
        select(EmbeddingModelTable.embedding_model_id)
        .join(
            CollectionEmbeddingModelTable,
            onclause=col(CollectionEmbeddingModelTable.embedding_model_id)
            == col(EmbeddingModelTable.embedding_model_id),
        )
        .where(
            CollectionEmbeddingModelTable.collection_id == collection_id,
            EmbeddingModelTable.name == embedding_model_name,
        )
    ).one_or_none()
    if embedding_model_id is None:
        raise ValueError(f"Embedding model with name `{embedding_model_name}` not found.")

    return embedding_model_id


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
