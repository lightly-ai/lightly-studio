"""Function to get a unique child collection with a given sample type and name."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver


def get_child_collection_by_name(session: Session, collection_id: UUID, name: str) -> UUID | None:
    """Gets the child collection with the given name.

    If it exists, returns its ID. If not, returns None.
    If multiple such collections exist, raises an error.

    The returned child is a direct child of the given collection.

    Args:
        session: The database session.
        collection_id: The UUID of the collection to search in.
        name: Name of the child collection.

    Returns:
        The UUID of the child collection if found, else None.

    Raises:
        ValueError: If multiple child collections with the given sample type and name exist.
        ValueError: If the collection with the given ID is not found.
    """
    # Get filtered child collections.
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    child_collections = [col for col in collection.children if _matches_name(col.name, name)]

    # If we have children check if any have the given sample type.
    if len(child_collections) == 1:
        return child_collections[0].collection_id
    if len(child_collections) > 1:
        raise ValueError(
            f"Multiple child collections with name {name} found for collection id {collection_id}."
        )

    return None


def _matches_name(collection_name: str, filter_name: str | None) -> bool:
    return filter_name is None or filter_name == collection_name
