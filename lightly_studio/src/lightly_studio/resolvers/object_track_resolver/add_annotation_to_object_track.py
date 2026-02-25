"""Link an existing annotation to a object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation.object_track import ObjectTrackTable
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver import annotation_helper


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
        return annotation_helper.update_annotation_object(
            session=session,
            annotation=annotation,
            fields_to_update={"object_track_id": object_track.object_track_id},
        )
    except Exception:
        session.rollback()
        raise
