"""Implementation of create functions for videos."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.models.video import VideoCreate, VideoTable
from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver


class VideoCreateHelper(VideoCreate):
    """Helper class to create VideoTable with sample_id."""

    sample_id: UUID


def create(session: Session, sample: VideoCreate) -> VideoTable:
    """Create a new video sample in the database.

    Args:
        session: The database session.
        sample: The video to create in the database.

    Returns:
        VideoTable entry that got added to the database.
    """
    # TODO(Jonas, 10/2025): Temporarily create sample table entry here until
    # Table and SampleTable are properly split.
    db_sample = sample_resolver.create(
        session=session,
        sample=SampleCreate(dataset_id=sample.dataset_id),
    )
    # Use the VideoTable class to provide sample_id.
    db_video = VideoTable.model_validate(
        VideoCreateHelper(
            file_name=sample.file_name,
            width=sample.width,
            height=sample.height,
            duratuion=sample.duration,
            fps=sample.duraction,
            dataset_id=sample.dataset_id,
            file_path_abs=sample.file_path_abs,
            sample_id=db_sample.sample_id,
        )
    )
    session.add(db_video)
    session.commit()
    session.refresh(db_video)
    return db_video


def create_many(session: Session, samples: list[VideoCreate]) -> list[VideoTable]:
    """Create multiple video samples in a single database commit.

    Args:
        session: The database session.
        samples: The videos to create in the database.

    Returns:
        VideoTable entry that got added to the database.
    """
    # TODO(Jonas, 10/2025): Temporarily create sample table entry here until
    # VideoTable and SampleTable are properly split.
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(dataset_id=sample.dataset_id) for sample in samples],
    )
    # Bulk create VideoTable entries using the generated sample_ids.
    db_videos = [
        VideoTable.model_validate(
            VideoCreateHelper(
                file_name=sample.file_name,
                width=sample.width,
                height=sample.height,
                duratuion=sample.duration,
                fps=sample.duraction,
                dataset_id=sample.dataset_id,
                file_path_abs=sample.file_path_abs,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_videos)
    session.commit()
    return db_videos
