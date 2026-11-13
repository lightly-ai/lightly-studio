"""Delete an object track by ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.object_track import ObjectTrackTable


def delete_by_id(session: Session, object_track_id: UUID, commit: bool = True) -> None:
    """Delete an object track unless it is referenced by a child track.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the object track to delete.
        commit: Whether to commit or leave changes in the caller's transaction.
    """
    child_id = session.exec(
        select(ObjectTrackTable.object_track_id).where(
            col(ObjectTrackTable.parent_object_track_id) == object_track_id
        )
    ).first()
    if child_id is not None:
        return

    track = session.exec(
        select(ObjectTrackTable).where(col(ObjectTrackTable.object_track_id) == object_track_id)
    ).first()
    if track is not None:
        session.delete(track)
        if commit:
            session.commit()
        else:
            session.flush()
