"""Implementation of create functions for video_frames."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.video import VideoFrameCreate, VideoFrameTable
from lightly_studio.resolvers import sample_resolver


class VideoFrameCreateHelper(VideoFrameCreate):
    """Helper class to create VideoFrameTable with sample_id."""

    sample_id: UUID


def create(
    session: Session,
    dataset_id: UUID,
    sample: VideoFrameCreate,
) -> VideoFrameTable:
    """Create a new video_frame sample in the database.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        sample: The video_frame to create in the database.

    Returns:
        VideoFrameTable entry that got added to the database.
    """
    # TODO(Jonas, 10/2025): Temporarily create sample table entry here until
    # Table and SampleTable are properly split.
    db_sample = sample_resolver.create(
        session=session,
        sample=SampleCreate(dataset_id=dataset_id),
    )
    # Use the VideoFrameTable class to provide sample_id.
    db_video_frame = VideoFrameTable.model_validate(
        VideoFrameCreateHelper(
            frame_number=sample.frame_number,
            frame_timestamp=sample.frame_timestamp,
            video_sample_id=sample.video_sample_id,
            sample_id=db_sample.sample_id,
        )
    )
    session.add(db_video_frame)
    session.commit()
    session.refresh(db_video_frame)
    return db_video_frame


def create_many(
    session: Session, dataset_id: UUID, samples: list[VideoFrameCreate]
) -> list[VideoFrameTable]:
    """Create multiple video_frame samples in a single database commit.

    Args:
        session: The database session.
        dataset_id: The uuid of the dataset to attach to.
        samples: The video_frames to create in the database.

    Returns:
        VideoFrameTable entry that got added to the database.
    """
    # TODO(Jonas, 10/2025): Temporarily create sample table entry here until
    # VideoFrameTable and SampleTable are properly split.
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
    return db_video_frames
