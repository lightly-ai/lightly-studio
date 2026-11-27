"""Implementation of the get collection table by name resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import joinedload
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_table_by_name(
    session: Session,
    name: str,
    parent_collection_id: UUID | None,
) -> CollectionTable | None:
    """Retrieves a single collection by its name and parent collection.

    The query also loads the group component definition of the collection.

    Args:
        session:
            The database session to use.
        name:
            The name of the collection to retrieve.
        parent_collection_id:
            The optional UUID of the parent collection. If None, the search
            is performed for root collections (collections with no parent).

    Returns:
        The collection if found, otherwise None.

    Raises:
        ValueError:
            If the specified parent_collection_id does not exist.
    """
    statement = (
        select(CollectionTable)
        .where(CollectionTable.name == name)
        .where(col(CollectionTable.parent_collection_id) == parent_collection_id)
        .options(joinedload(CollectionTable.group_component_definition))  # type: ignore[arg-type]
    )
    collection = session.exec(statement).one_or_none()
    if (
        collection is None
        and parent_collection_id is not None
        and collection_resolver.get_by_id(session=session, collection_id=parent_collection_id)
        is None
    ):
        raise ValueError(f"Parent collection with id {parent_collection_id} not found.")
    return collection
