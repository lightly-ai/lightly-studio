"""Link an existing annotation to a object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.object_track_resolver.update_annotation_object_track_id import (
    update_annotation_object_track_id,
)


def add_annotation_to_object_track(
    session: Session,
    annotation_id: UUID,
    object_track: ObjectTrackTable,
) -> AnnotationBaseTable:
    """Link an existing annotation to a object track by setting its tracking_id.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to link.
        object_track: The object track to link the annotation to.

    Returns:
        The updated annotation with tracking_id set.
    """
    annotation = annotation_resolver.get_by_id(session, annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    try:
        return update_annotation_object_track_id(
            session,
            annotation=annotation,
            object_track_id=object_track.object_track_id,
            flush=True,
        )
    except Exception:
        session.rollback()
        raise
