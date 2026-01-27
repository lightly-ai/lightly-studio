"""Function to get or create a unique child collection with a given sample type."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def get_or_create_child_collection(
    session: Session, collection_id: UUID, sample_type: SampleType, name: str | None = None
) -> UUID:
    """Checks if a unique child with the given sample type exists for the given collection.

    If it exists, returns its ID. If not, creates it and then returns its ID.
    If multiple such collections exist, raises an error.

    The returned child is a direct child of the given collection.

    Args:
        session: The database session.
        collection_id: The uuid of the collection to attach to.
        sample_type: The sample type of the child collection to get or create.
        name: Optional name of the child collection. If None, a default name is set.

    Returns:
        The uuid of the child collection.

    Raises:
        ValueError: If multiple child collections with the given sample type exist.
    """
    # Get filtered child collections.
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    child_collections = [
        col
        for col in collection.children
        if col.sample_type == sample_type
        and _matches_name(collection_name=col.name, filter_name=name)
    ]

    # If we have children check if any have the given sample type.
    if len(child_collections) == 1:
        return child_collections[0].collection_id
    if len(child_collections) > 1:
        raise ValueError(
            f"Multiple child collections with sample type {sample_type.value} found "
            f"for collection id {collection_id}."
        )

    name = name or f"{collection.name}__{sample_type.value.lower()}"
    # No child collection with the given sample type found, create one.
    child_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=name,
            sample_type=sample_type,
            parent_collection_id=collection_id,
        ),
    )
    return child_collection.collection_id


def _matches_name(collection_name: str, filter_name: str | None) -> bool:
    return filter_name is None or filter_name == collection_name
