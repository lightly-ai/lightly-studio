"""Implementation of get_child_collections resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dataset import DatasetTable


def get_hierarchy(session: Session, dataset_id: UUID) -> list[CollectionTable]:
    """Retrieve all collections of the given dataset.

    The collections are returned in the depth-first order, starting with the root collection.
    The relative order of children of any given node is the order in CollectionTable.children.
    """
    # Ensure dataset exists.
    if session.get(DatasetTable, dataset_id) is None:
        raise ValueError(f"Dataset with id {dataset_id} not found.")

    # Find the root collection of the dataset.
    root_collection = session.exec(
        select(CollectionTable).where(
            col(CollectionTable.dataset_id) == dataset_id,
            col(CollectionTable.parent_collection_id).is_(None),
        )
    ).first()

    if root_collection is None:
        # Note: this is a bug in dataset/collection creation. We've created a dataset without any
        # collections.
        raise RuntimeError(f"Root collection of dataset {dataset_id} not found")

    # Use a stack to perform depth-first traversal of the collection hierarchy.
    to_process = [root_collection]
    all_collections = []
    while to_process:
        current_collection = to_process.pop()
        all_collections.append(current_collection)
        to_process.extend(reversed(current_collection.children))

    return all_collections
