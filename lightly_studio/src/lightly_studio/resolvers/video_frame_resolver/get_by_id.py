"""Retrieve the video frame by ID resolver implementation."""

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.video import VideoFrameTable


def get_by_id(session: Session, sample_id: UUID) -> VideoFrameTable:
    """Retrieve a single video frame by ID within a collection."""
    query = select(VideoFrameTable).where(VideoFrameTable.sample_id == sample_id)
    return session.exec(query).one()
