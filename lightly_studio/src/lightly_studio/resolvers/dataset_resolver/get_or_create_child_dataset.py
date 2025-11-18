"""Function to get or create a unique child dataset with a given sample type."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, SampleType
from lightly_studio.resolvers import dataset_resolver


def get_or_create_child_dataset(
    session: Session, dataset_id: UUID, sample_type: SampleType
) -> UUID:
    """Checks if a unique child dataset with the given sample type exists for the given dataset.

    If it exists, returns its ID. If not, creates it and then returns its ID.
    If multiple such datasets exist, raises an error.

    The returned child is a direct child of the given dataset.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        sample_type: The sample type of the child dataset to get or create.

    Returns:
        The uuid of the child dataset.

    Raises:
        ValueError: If multiple child datasets with the given sample type exist.
    """
    # Get filtered child datasets.
    dataset = dataset_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if dataset is None:
        raise ValueError(f"Dataset with id {dataset_id} not found.")
    child_datasets = [ds for ds in dataset.children if ds.sample_type == sample_type]

    # If we have children check if any have the given sample type.
    if len(child_datasets) == 1:
        return child_datasets[0].dataset_id
    if len(child_datasets) > 1:
        raise ValueError(
            f"Multiple child datasets with sample type {sample_type} found "
            f"for dataset id {dataset_id}."
        )

    # No child dataset with the given sample type found, create one.
    child_dataset = dataset_resolver.create(
        session=session,
        dataset=DatasetCreate(
            name=f"{dataset.name}__{sample_type.name.lower()}",
            sample_type=sample_type,
            parent_dataset_id=dataset_id,
        ),
    )
    return child_dataset.dataset_id
