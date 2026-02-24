"""Create an object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def create_object_track(
    session: Session,
    object_track_number: int,
    dataset_id: UUID,
) -> ObjectTrackTable:
    """Create a new object track.

    Args:
        session: Database session for executing the operation.
        object_track_number: Numeric identifier for the track.
        dataset_id: UUID of the root collection the track belongs to.

    Returns:
        The created ObjectTrackTable instance.
    """
    track = ObjectTrackTable(
        object_track_number=object_track_number,
        dataset_id=dataset_id,
    )
    session.add(track)
    session.commit()
    session.refresh(track)
    return track
