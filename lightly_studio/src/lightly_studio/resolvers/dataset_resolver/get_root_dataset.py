"""Implementation of get_root_dataset resolver function."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.dataset import DatasetTable


def get_root_dataset(session: Session) -> DatasetTable:
    """Retrieve the root dataset (a dataset with no parent).

    A root dataset is defined as a dataset where parent_dataset_id is None.
    The root dataset may or may not have children.

    Args:
        session: The database session.

    Returns:
        The root dataset.

    Raises:
        ValueError: If no root dataset is found or if multiple root datasets exist.
    """
    root_datasets = session.exec(
        select(DatasetTable).where(col(DatasetTable.parent_dataset_id).is_(None))
    ).all()

    if len(root_datasets) == 0:
        raise ValueError("No root dataset found. A root dataset must exist.")

    return root_datasets[0]
