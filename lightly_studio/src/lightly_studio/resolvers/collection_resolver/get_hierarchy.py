"""Implementation of get_child_datasets resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import collection_resolver


def get_hierarchy(session: Session, root_dataset_id: UUID) -> list[CollectionTable]:
    """Retrieve all child datasets of the given root dataset, including the root itself.

    The datasets are returned in the depth-first order, starting with the root dataset.
    The relative order of children of any given node is the order in CollectionTable.children.
    """
    root_dataset = collection_resolver.get_by_id(session=session, dataset_id=root_dataset_id)
    if root_dataset is None:
        raise ValueError(f"Dataset with id {root_dataset_id} not found.")

    # Use a stack to perform depth-first traversal of the dataset hierarchy.
    to_process = [root_dataset]
    all_datasets = []
    while to_process:
        current_dataset = to_process.pop()
        all_datasets.append(current_dataset)
        to_process.extend(reversed(current_dataset.children))

    return all_datasets
