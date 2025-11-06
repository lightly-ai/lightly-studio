"""Implementation of create functions for video_frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.video import VideoFrameCreate, VideoFrameTable
from lightly_studio.resolvers import dataset_resolver, sample_resolver


class VideoFrameCreateHelper(VideoFrameCreate):
    """Helper class to create VideoFrameTable with sample_id."""

    sample_id: UUID


def create_many(session: Session, dataset_id: UUID, samples: list[VideoFrameCreate]) -> list[UUID]:
    """Create multiple video_frame samples in a single database commit.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        samples: The video_frames to create in the database.

    Returns:
        List of UUIDs of VideoFrameTable entries that got added to the database.
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
    # Bulk create VideoFrameTable entries using the generated sample_ids.
    db_video_frames = [
        VideoFrameTable.model_validate(
            VideoFrameCreateHelper(
                frame_number=sample.frame_number,
                frame_timestamp=sample.frame_timestamp,
                video_sample_id=sample.video_sample_id,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_video_frames)
    session.commit()
    return sample_ids
