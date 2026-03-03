"""Get all annotations for an object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)


def get_all_by_object_track_id(
    session: Session,
    object_track_id: UUID,
    annotation_types: list[AnnotationType] | None = None,
) -> list[AnnotationBaseTable]:
    """Retrieve all annotations belonging to a given object track.

    Args:
        session: Database session for executing the operation.
        object_track_id: UUID of the object track.
        annotation_types: If set, only return annotations with one of these types.
            If None, return all annotations for the track.

    Returns:
        List of annotations belonging to the track.
    """
    query = (
        select(AnnotationBaseTable)
        .where(col(AnnotationBaseTable.object_track_id) == object_track_id)
        .order_by(
            col(AnnotationBaseTable.created_at).asc(),
            col(AnnotationBaseTable.sample_id).asc(),
        )
    )
    if annotation_types is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type).in_(annotation_types))
    return list(session.exec(query).all())
