"""Delete an object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def delete_by_id(session: Session, object_track_id: UUID) -> None:
    """Delete a track that no annotation refers to any more.

    Args:
        session: The database session.
        object_track_id: The track to delete. Nothing happens if it does not exist.
    """
    track = session.get(ObjectTrackTable, object_track_id)
    if track is None:
        return
    session.delete(track)
    session.commit()
