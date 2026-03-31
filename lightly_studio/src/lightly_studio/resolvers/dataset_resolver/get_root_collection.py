"""Find the root collection of the dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.dataset import DatasetTable


def get_root_collection(session: Session, dataset_id: UUID) -> CollectionTable:
    """Find the root collection of the dataset.

    Args:
        session: Database session.
        dataset_id: Dataset ID.

    Returns:
        The root collection.

    Raises:
        ValueError: If dataset does not exist.
        RuntimeError: If root collection is not found.
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

    return root_collection
