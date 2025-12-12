"""Implementation of get_root_dataset resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.dataset import DatasetTable


# TODO (Mihnea, 12/2025): Update the dataset_id to be required.
#  The dataset_id is currently optional for backwards compatibility.
def get_root_dataset(session: Session, dataset_id: UUID | None = None) -> DatasetTable:
    """Retrieve the root dataset for a given dataset or the first root dataset.

    If dataset_id is provided, traverses up the hierarchy to find the root ancestor.
    If dataset_id is None, returns the first root dataset (backwards compatibility).

    A root dataset is defined as a dataset where parent_dataset_id is None.
    The root dataset may or may not have children.

    Args:
        session: The database session.
        dataset_id: Optional ID of a dataset to find the root for.

    Returns:
        The root dataset.

    Raises:
        ValueError: If no root dataset is found or dataset_id doesn't exist.
    """
    if dataset_id is not None:
        # Find the dataset.
        dataset = session.get(DatasetTable, dataset_id)
        if dataset is None:
            raise ValueError(f"Dataset with ID {dataset_id} not found.")

        # Traverse up the hierarchy until we find the root.
        # TODO (Mihnea, 12/2025): Consider replacing the loop with a recursive CTE,
        #  if this becomes a bottleneck.
        while dataset.parent_dataset_id is not None:
            parent = session.get(DatasetTable, dataset.parent_dataset_id)
            if parent is None:
                raise ValueError(
                    f"Parent dataset {dataset.parent_dataset_id} not found "
                    f"for dataset {dataset.dataset_id}."
                )
            dataset = parent

        return dataset

    # Backwards compatibility: return first root dataset
    root_datasets = session.exec(
        select(DatasetTable).where(col(DatasetTable.parent_dataset_id).is_(None))
    ).all()

    if len(root_datasets) == 0:
        raise ValueError("No root dataset found. A root dataset must exist.")

    return root_datasets[0]
