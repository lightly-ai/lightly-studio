"""Implementation of create functions for videos."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.video import VideoCreate, VideoTable
from lightly_studio.resolvers import dataset_resolver, sample_resolver


class VideoCreateHelper(VideoCreate):
    """Helper class to create VideoTable with sample_id."""

    sample_id: UUID


def create_many(session: Session, dataset_id: UUID, samples: list[VideoCreate]) -> list[UUID]:
    """Create multiple video samples in a single database commit.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        samples: The videos to create in the database.

    Returns:
        List of IDs of VideoTable entries that got added to the database.
    """
    dataset_resolver.check_dataset_type(
        session=session,
        dataset_id=dataset_id,
        expected_type=SampleType.VIDEO,
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(dataset_id=dataset_id) for _ in samples],
    )
    # Bulk create VideoTable entries using the generated sample_ids.
    db_videos = [
        VideoTable.model_validate(
            VideoCreateHelper(
                file_name=sample.file_name,
                width=sample.width,
                height=sample.height,
                duration=sample.duration,
                fps=sample.fps,
                file_path_abs=sample.file_path_abs,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_videos)
    session.commit()
    return [video.sample_id for video in db_videos]
