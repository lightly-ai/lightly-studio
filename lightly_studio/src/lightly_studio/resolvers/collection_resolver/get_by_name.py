"""Implementation of the get collection by name resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_by_name(
    session: Session,
    name: str,
    parent_collection_id: UUID | None,
) -> UUID | None:
    """Retrieves a single collection by its name and parent collection.

    Args:
        session:
            The database session to use.
        name:
            The name of the collection to retrieve.
        parent_collection_id:
            The optional UUID of the parent collection. If None, the search
            is performed for root collections (collections with no parent).

    Returns:
        The collection ID if found, otherwise None.

    Raises:
        ValueError:
            If the specified parent_collection_id does not exist.
    """
    if parent_collection_id is not None:
        parent = collection_resolver.get_by_id(session=session, collection_id=parent_collection_id)
        if parent is None:
            raise ValueError(f"Parent collection with id {parent_collection_id} not found.")
    statement = (
        select(CollectionTable)
        .where(CollectionTable.name == name)
        .where(col(CollectionTable.parent_collection_id) == parent_collection_id)
    )

    collection = session.exec(statement).one_or_none()
    if collection is not None:
        return collection.collection_id
    return None
