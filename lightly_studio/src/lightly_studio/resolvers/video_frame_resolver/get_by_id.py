"""Retrieve the video frame by ID resolver implementation."""

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable


def get_by_id(session: Session, dataset_id: UUID, sample_id: UUID) -> VideoFrameTable:
    """Retrieve a single video frame by ID within a dataset."""
    query = (
        select(VideoFrameTable)
        .join(VideoFrameTable.sample)
        .where(VideoFrameTable.sample_id == sample_id, SampleTable.dataset_id == dataset_id)
    )
    return session.exec(query).one()
