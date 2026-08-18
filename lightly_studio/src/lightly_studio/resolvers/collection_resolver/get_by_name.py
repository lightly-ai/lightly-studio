"""Implementation of the get collection by name resolver function."""

from __future__ import annotations

from uuid import UUID

import sqlalchemy
from sqlmodel import Session, col, select

from lightly_studio.errors import DuplicateCollectionNameError
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
        DuplicateCollectionNameError:
            If more than one collection matches the given name and parent. This
            signals a data integrity issue rather than a normal not-found case.
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

    try:
        collection = session.exec(statement).one_or_none()
    except sqlalchemy.exc.MultipleResultsFound as e:
        raise DuplicateCollectionNameError(
            f"Found multiple collections named '{name}' under parent "
            f"{parent_collection_id}. Collection names are expected to be unique "
            f"per parent."
        ) from e
    if collection is not None:
        return collection.collection_id
    return None
