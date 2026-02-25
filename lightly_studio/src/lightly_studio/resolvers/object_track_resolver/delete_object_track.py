"""Delete a object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import object_track_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper


def delete_object_track(
    session: Session,
    object_track_id: UUID,
) -> None:
    """Delete a track and unlink all its annotations.

    Annotations that belonged to the track are not deleted; their tracking_id
    is cleared so they remain as standalone annotations.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the track to delete.

    Raises:
        ValueError: If the track is not found.
    """
    track = object_track_resolver.get_by_id(session=session, object_track_id=object_track_id)
    if track is None:
        raise ValueError(f"Track {object_track_id} not found.")

    try:
        annotations = session.exec(
            select(AnnotationBaseTable).where(
                col(AnnotationBaseTable.object_track_id) == object_track_id
            )
        ).all()
        for annotation in annotations:
            annotation_helper.update_annotation_object(
                session=session,
                annotation=annotation,
                fields_to_update={"object_track_id": None},
            )

        session.delete(track)
        session.commit()
    except Exception:
        session.rollback()
        raise
