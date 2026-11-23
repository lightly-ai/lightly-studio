"""Update the polygons of a polygon annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation.polygon import Polygons, validate_polygons
from lightly_studio.resolvers import annotation_resolver


def update_polygons(
    session: Session, annotation_id: UUID, polygons: Polygons
) -> AnnotationBaseTable:
    """Replace the polygons of an annotation and recompute its bounding box.

    Args:
        session: Database session.
        annotation_id: The annotation ID to update.
        polygons: The new polygon parts. Each part is a list of (x, y) vertices.

    Returns:
        The updated AnnotationBaseTable instance.

    Raises:
        ValueError: If the annotation does not exist, is not a polygon, or the polygons are
            invalid.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")

    details = annotation.polygon_details
    if not details:
        raise ValueError("Annotation type does not support polygons.")

    validated = validate_polygons(polygons=polygons)
    try:
        details.polygons = validated.polygons
        details.x = validated.x
        details.y = validated.y
        details.width = validated.width
        details.height = validated.height
        session.add(details)
        session.commit()
        session.refresh(annotation)
        return annotation
    except Exception:
        session.rollback()
        raise
