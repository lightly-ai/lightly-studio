"""General annotation update service."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate


def update_annotations(
    session: Session, annotation_updates: list[AnnotationUpdate]
) -> list[AnnotationBaseTable]:
    """Update multiple annotations.

    Args:
        session: Database session for executing the operation.
        annotation_updates: List of objects containing updates for the annotations.

    Returns:
        List of updated annotations.
    """
    return [
        annotations_service.update_annotation(session, annotation_update)
        for annotation_update in annotation_updates
    ]
