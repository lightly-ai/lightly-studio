"""General annotation update service."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.services import annotations_service


class AnnotationUpdate(BaseModel):
    """Model for updating an annotation."""

    annotation_id: UUID
    dataset_id: UUID
    label_name: str | None = None
    bounding_box: BoundingBoxCoordinates | None = None


def update_annotation(session: Session, annotation_update: AnnotationUpdate) -> AnnotationBaseTable:
    """Update an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_update: Object containing updates for the annotation.

    Returns:
        The updated annotation.

    """
    result = None
    if annotation_update.label_name is not None:
        result = annotations_service.update_annotation_label(
            session,
            annotation_update.annotation_id,
            annotation_update.label_name,
        )

    if annotation_update.bounding_box is not None:
        result = annotations_service.update_annotation_bounding_box(
            session,
            annotation_update.annotation_id,
            bounding_box=annotation_update.bounding_box,
        )

    if result is None:
        raise ValueError("No updates provided for the annotation.")
    return result
