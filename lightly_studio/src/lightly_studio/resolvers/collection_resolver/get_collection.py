"""Implementation of get_root_collection resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


# TODO (Mihnea, 12/2025): Update the collection_id to be required.
#  The collection_id is currently optional for backwards compatibility.
def get_dataset(session: Session, collection_id: UUID | None = None) -> CollectionTable:
    """Retrieve the root collection for a given collection or the first root collection.

    If collection_id is provided, traverses up the hierarchy to find the root ancestor.
    If collection_id is None, returns the first root collection (backwards compatibility).

    A root collection (dataset) is defined as a collection where parent_collection_id is None.
    The root collection may or may not have children.

    Args:
        session: The database session.
        collection_id: Optional ID of a collection to find the root for.

    Returns:
        The root collection.

    Raises:
        ValueError: If no root collection is found or collection_id doesn't exist.
    """
    if collection_id is not None:
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

    # Backwards compatibility: return first root collection
    root_collections = session.exec(
        select(CollectionTable).where(col(CollectionTable.parent_collection_id).is_(None))
    ).all()

    if len(root_collections) == 0:
        raise ValueError("No root collection found. A root collection must exist.")

    return root_collections[0]
