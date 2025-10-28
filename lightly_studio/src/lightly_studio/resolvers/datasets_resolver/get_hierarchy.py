"""Implementation of get_child_datasets resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetTable
from lightly_studio.resolvers import dataset_resolver


def get_hierarchy(session: Session, root_dataset_id: UUID) -> list[DatasetTable]:
    """Retrieve all child datasets of the given root dataset, including the root itself."""
    root_dataset = dataset_resolver.get_by_id(session=session, dataset_id=root_dataset_id)
    if root_dataset is None:
        raise ValueError(f"Dataset with id {root_dataset_id} not found.")

    to_process = [root_dataset]
    all_datasets = []
    while to_process:
        current_dataset = to_process.pop()
        all_datasets.append(current_dataset)
        to_process.extend(current_dataset.children)

    return all_datasets
