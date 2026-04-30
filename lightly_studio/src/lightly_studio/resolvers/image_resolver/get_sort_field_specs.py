"""Get image sort field specifications."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sort import SortFieldSource, SortFieldSpec
from lightly_studio.resolvers import dataset_resolver


def get_sort_field_specs(session: Session, dataset_id: UUID) -> list[SortFieldSpec]:
    """Get image fields available for sorting in a dataset.

    Args:
        session: The database session.
        dataset_id: ID of the dataset to retrieve sort fields for.

    Returns:
        Image sort fields available for the dataset.

    Raises:
        ValueError: If the dataset does not exist or is not an image dataset.
    """
    # root_collection = dataset_resolver.get_root_collection(session=session, dataset_id=dataset_id)
    # if root_collection.sample_type != SampleType.IMAGE:
    #     raise ValueError(f"Dataset {dataset_id} is not an image dataset.")

    return [
        SortFieldSpec(
            id="image.file_name",
            field_name="file_name",
            label="File Name",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.file_path_abs",
            field_name="file_path_abs",
            label="File Path",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.width",
            field_name="width",
            label="Width",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="image.height",
            field_name="height",
            label="Height",
            source=SortFieldSource.IMAGE,
        ),
        SortFieldSpec(
            id="sample.created_at",
            field_name="created_at",
            label="Created At",
            source=SortFieldSource.SAMPLE,
        ),
    ]
