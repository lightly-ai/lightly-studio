"""Returns a video frame child dataset for a given video dataset, creating it if necessary."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import DatasetCreate, SampleType
from lightly_studio.resolvers import dataset_resolver


def get_or_create_video_frame_child(session: Session, dataset_id: UUID) -> UUID:
    """Checks if a child dataset with video frame sample type exists for the given dataset.

    If it exists, returns its ID. If not, creates it and then returns its ID.
    If multiple video frame child datasets exist, raises an error.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.

    Returns:
        The uuid of the video frame child dataset.

    Raises:
        ValueError: If multiple video frame child datasets exist for the given dataset.
    """
    # Ensure the dataset is of type VIDEO.
    # Only video datasets should have video frame child datasets.
    dataset_resolver.check_dataset_type(
        session=session,
        dataset_id=dataset_id,
        expected_type=SampleType.VIDEO,
    )
    datasets = dataset_resolver.get_hierarchy(
        session=session,
        root_dataset_id=dataset_id,
    )
    # If we have children check if any have video frame sample types.
    video_frame_datasets = [ds for ds in datasets if ds.sample_type == SampleType.VIDEO_FRAME]
    if len(video_frame_datasets) == 1:
        return video_frame_datasets[0].dataset_id
    if len(video_frame_datasets) > 1:
        raise ValueError(f"Multiple video frame child datasets found for dataset id {dataset_id}.")
    # No child dataset with video frame sample type found, create one.
    child_dataset = dataset_resolver.create(
        session=session,
        dataset=DatasetCreate(
            name=f"{datasets[0].name}__video_frames",
            sample_type=SampleType.VIDEO_FRAME,
            parent_dataset_id=dataset_id,
        ),
    )
    return child_dataset.dataset_id
