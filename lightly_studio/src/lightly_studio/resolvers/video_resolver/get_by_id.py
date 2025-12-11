"""Find a video by its id."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.video import VideoTable


def get_by_id(session: Session, sample_id: UUID) -> VideoTable | None:
    """Retrieve a single video sample by ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A VideoTable object or none.
    """
    return session.exec(select(VideoTable).where(VideoTable.sample_id == sample_id)).one()
