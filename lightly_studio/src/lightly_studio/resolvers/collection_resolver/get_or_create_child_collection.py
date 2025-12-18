"""Function to get or create a unique child collection with a given sample type."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def get_or_create_child_collection(
    session: Session, collection_id: UUID, sample_type: SampleType
) -> UUID:
    """Checks if a unique child with the given sample type exists for the given collection.

    If it exists, returns its ID. If not, creates it and then returns its ID.
    If multiple such collections exist, raises an error.

    The returned child is a direct child of the given collection.

    Args:
        session: The database session.
        collection_id: The uuid of the collection to attach to.
        sample_type: The sample type of the child collection to get or create.

    Returns:
        The uuid of the child collection.

    Raises:
        ValueError: If multiple child collections with the given sample type exist.
    """
    # Get filtered child collections.
    collection = collection_resolver.get_by_id(session=session, dataset_id=collection_id)
    if collection is None:
        raise ValueError(f"collection with id {collection_id} not found.")
    child_collections = [ds for ds in collection.children if ds.sample_type == sample_type]

    # If we have children check if any have the given sample type.
    if len(child_collections) == 1:
        return child_collections[0].collection_id
    if len(child_collections) > 1:
        raise ValueError(
            f"Multiple child collections with sample type {sample_type.value} found "
            f"for collection id {collection_id}."
        )

    # No child collection with the given sample type found, create one.
    child_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(
            name=f"{collection.name}__{sample_type.value.lower()}",
            sample_type=sample_type,
            parent_collection_id=collection_id,
        ),
    )
    return child_collection.collection_id
