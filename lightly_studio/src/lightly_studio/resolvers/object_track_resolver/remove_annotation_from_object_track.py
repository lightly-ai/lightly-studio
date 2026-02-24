"""Unlink an annotation from its object track."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.object_track_resolver.update_annotation_object_track_id import (
    update_annotation_object_track_id,
)


def remove_annotation_from_object_track(
    session: Session,
    annotation_id: UUID,
) -> AnnotationBaseTable:
    """Unlink an annotation from its current object track by clearing its tracking_id.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to unlink.

    Returns:
        The updated annotation with tracking_id cleared.
    """
    annotation = annotation_resolver.get_by_id(session, annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    try:
        return update_annotation_object_track_id(
            session,
            annotation=annotation,
            object_track_id=None,
            flush=True,
        )
    except Exception:
        session.rollback()
        raise
