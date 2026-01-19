"""Module for handling the update of annotation bounding box coordinates in the database."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_resolver


@dataclass
class BoundingBoxCoordinates:
    """Represents bounding box coordinates."""

    x: int
    y: int
    width: int
    height: int


def update_bounding_box(
    session: Session,
    annotation_id: UUID,
    coordinates: BoundingBoxCoordinates,
) -> AnnotationBaseTable:
    """Update the bounding box coordinates of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        coordinates: New bounding box coordinates.

    Returns:
        The updated annotation with the new bounding box coordinates.

    Raises:
        ValueError: If the annotation is not found.
    """
    annotation = annotation_resolver.get_by_id(session, annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")

    try:
        if annotation.object_detection_details:
            annotation.object_detection_details.x = coordinates.x
            annotation.object_detection_details.y = coordinates.y
            annotation.object_detection_details.width = coordinates.width
            annotation.object_detection_details.height = coordinates.height
            session.add(annotation.object_detection_details)

        elif annotation.segmentation_details:
            annotation.segmentation_details.x = coordinates.x
            annotation.segmentation_details.y = coordinates.y
            annotation.segmentation_details.width = coordinates.width
            annotation.segmentation_details.height = coordinates.height
            session.add(annotation.segmentation_details)
        else:
            raise ValueError("Annotation type does not support bounding boxes.")

        session.commit()
        session.refresh(annotation)
        return annotation
    except Exception:
        session.rollback()
        raise
