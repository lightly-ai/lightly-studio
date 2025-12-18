"""Implementation of create functions for videos."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.video import VideoCreate, VideoTable
from lightly_studio.resolvers import collection_resolver, sample_resolver


class VideoCreateHelper(VideoCreate):
    """Helper class to create VideoTable with sample_id."""

    sample_id: UUID


def create_many(session: Session, collection_id: UUID, samples: list[VideoCreate]) -> list[UUID]:
    """Create multiple video samples in a single database commit.

    Args:
        session: The database session.
        collection_id: The uuid of the collection to attach to.
        samples: The videos to create in the database.

    Returns:
        List of IDs of VideoTable entries that got added to the database.
    """
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.VIDEO,
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id) for _ in samples],
    )
    # Bulk create VideoTable entries using the generated sample_ids.
    db_videos = [
        VideoTable.model_validate(
            VideoCreateHelper(
                file_name=sample.file_name,
                width=sample.width,
                height=sample.height,
                duration_s=sample.duration_s,
                fps=sample.fps,
                file_path_abs=sample.file_path_abs,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_videos)
    session.commit()
    return sample_ids
