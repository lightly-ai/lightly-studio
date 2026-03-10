"""Get an object track by its ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def get_by_id(
    session: Session,
    object_track_id: UUID,
) -> ObjectTrackTable | None:
    """Retrieve a single track by its object_track_id.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the track to retrieve.

    Returns:
        The ObjectTrackTable instance, or None if not found.
    """
    return session.exec(
        select(ObjectTrackTable).where(col(ObjectTrackTable.object_track_id) == object_track_id)
    ).one_or_none()
