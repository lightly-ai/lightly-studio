"""Implementation of check_dataset_type resolver function."""

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver


def check_dataset_type(session: Session, dataset_id: UUID, expected_type: SampleType) -> None:
    """Check that the dataset has the expected sample type.

    Raises a ValueError if the dataset does not have the expected sample type or
    if it does not exist.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to check.
        expected_type: The expected sample type.
    """
    dataset = collection_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if dataset is None:
        raise ValueError(f"Dataset with id {dataset_id} not found.")
    if dataset.sample_type != expected_type:
        raise ValueError(
            f"Dataset with id {dataset_id} is having sample type "
            f"'{dataset.sample_type.value}', expected '{expected_type.value}'."
        )
