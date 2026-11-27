"""Delete object tracks that have no annotations and no child tracks."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, delete, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.utils import batching


def delete_empty_by_ids(session: Session, object_track_ids: Sequence[UUID]) -> int:
    """Delete the given object tracks that have no annotations and no child tracks.

    When a track is deleted, its parent track is also checked and deleted if it becomes
    empty. Tracks that have annotations or child tracks are kept. IDs that do not exist
    are ignored.

    Args:
        session: Database session.
        object_track_ids: IDs of the object tracks to check.

    Returns:
        The number of deleted object tracks.
    """
    candidate_ids = set(object_track_ids)
    deleted_count = 0
    while candidate_ids:
        parent_id_by_empty_id = _get_empty_tracks(session=session, object_track_ids=candidate_ids)
        if not parent_id_by_empty_id:
            break
        # A track with child tracks is not empty. Thus a parent track is deleted in a later
        # pass than its child tracks, and the parent foreign key stays valid.
        for batch in batching.batched(items=parent_id_by_empty_id):
            session.exec(
                delete(ObjectTrackTable).where(col(ObjectTrackTable.object_track_id).in_(batch)),
                execution_options={"synchronize_session": False},
            )
        session.commit()
        deleted_count += len(parent_id_by_empty_id)
        candidate_ids = {
            parent_id for parent_id in parent_id_by_empty_id.values() if parent_id is not None
        }
    return deleted_count


def _get_empty_tracks(session: Session, object_track_ids: set[UUID]) -> dict[UUID, UUID | None]:
    """Map each track without annotations and child tracks to its parent track ID."""
    has_annotation = (
        select(AnnotationBaseTable.object_track_id)
        .where(col(AnnotationBaseTable.object_track_id) == ObjectTrackTable.object_track_id)
        .exists()
    )
    child_track = aliased(ObjectTrackTable)
    has_child_track = (
        select(child_track.object_track_id)
        .where(col(child_track.parent_object_track_id) == ObjectTrackTable.object_track_id)
        .exists()
    )
    parent_id_by_empty_id: dict[UUID, UUID | None] = {}
    for batch in batching.batched(items=object_track_ids):
        rows = session.exec(
            select(ObjectTrackTable.object_track_id, ObjectTrackTable.parent_object_track_id).where(
                col(ObjectTrackTable.object_track_id).in_(batch),
                ~has_annotation,
                ~has_child_track,
            )
        ).all()
        parent_id_by_empty_id.update(dict(rows))
    return parent_id_by_empty_id
