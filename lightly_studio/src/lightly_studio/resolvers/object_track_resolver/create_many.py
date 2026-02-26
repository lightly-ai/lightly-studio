"""Implementation of create_many for object track resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.object_track import ObjectTrackCreate, ObjectTrackTable


def create_many(session: Session, tracks: list[ObjectTrackCreate]) -> list[UUID]:
    """Create multiple object tracks in a single database commit.

    Args:
        session: The database session.
        tracks: The object tracks to create in the database.

    Returns:
        List of UUIDs of ObjectTrackTable entries that got added to the database.
    """
    if not tracks:
        return []

    db_tracks = [ObjectTrackTable.model_validate(track.model_dump()) for track in tracks]
    session.bulk_save_objects(db_tracks)
    session.commit()
    return [track.object_track_id for track in db_tracks]
