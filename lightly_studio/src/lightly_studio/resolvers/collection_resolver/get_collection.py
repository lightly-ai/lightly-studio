"""Implementation of get_root_collection resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable


def get_root_collection(session: Session, collection_id: UUID) -> CollectionTable:
    """Retrieve the root collection for a given collection.

    Traverses up the hierarchy to find the root ancestor.

    A root collection (dataset) is defined as a collection where parent_collection_id is None.
    The root collection may or may not have children.

    Args:
        session: The database session.
        collection_id: ID of a collection to find the root for.

    Returns:
        The root collection.

    Raises:
        ValueError: If collection_id doesn't exist.
    """
    # Find the collection.
    collection = session.get(CollectionTable, collection_id)
    if collection is None:
        raise ValueError(f"Collection with ID {collection_id} not found.")

    # Traverse up the hierarchy until we find the root.
    # TODO (Mihnea, 12/2025): Consider replacing the loop with a recursive CTE,
    #  if this becomes a bottleneck.
    while collection.parent_collection_id is not None:
        parent = session.get(CollectionTable, collection.parent_collection_id)
        if parent is None:
            raise ValueError(
                f"Parent collection {collection.parent_collection_id} not found "
                f"for collection {collection.collection_id}."
            )
        collection = parent

    return collection
