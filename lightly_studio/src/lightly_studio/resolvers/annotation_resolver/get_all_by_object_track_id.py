"""Get all annotations for an object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable


def get_all_by_object_track_id(
    session: Session,
    object_track_id: UUID,
) -> list[AnnotationBaseTable]:
    """Retrieve all annotations belonging to a given object track.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the object track.

    Returns:
        List of annotations belonging to the track.
    """
    return list(
        session.exec(
            select(AnnotationBaseTable)
            .where(col(AnnotationBaseTable.object_track_id) == object_track_id)
            .order_by(
                col(AnnotationBaseTable.created_at).asc(), col(AnnotationBaseTable.sample_id).asc()
            )
        ).all()
    )
