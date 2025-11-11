"""Find a video by its id."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.video import VideoTable


def get_by_id(session: Session, sample_id: UUID) -> VideoTable | None:
    """Retrieve a video for a given dataset ID by its ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A video object or none.
    """
    query = select(VideoTable).where(
        VideoTable.sample_id == sample_id,
    )
    return session.exec(query).one()
