"""Update the instance segmentation segmentation mask field."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_resolver


def update_segmentation_mask(
    session: Session, annotation_id: UUID, segmentation_mask: list[int]
) -> AnnotationBaseTable:
    """This function retrieves an annotation by its ID, updates the segmentation_mask field.

    Args:
        session: Database session.
        annotation_id: The annotation ID to update.
        segmentation_mask: The new segmentation mask values as a list of integers.

    Returns:
        The updated AnnotationBaseTable instance.

    Raises:
        ValueError: If the annotation does not exist or does not support a segmentation mask.
    """
    annotation = annotation_resolver.get_by_id(session, annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")

    if not annotation.segmentation_details:
        raise ValueError("Annotation type does not support segmentation mask.")

    try:
        annotation.segmentation_details.segmentation_mask = segmentation_mask

        session.commit()
        session.refresh(annotation)
        return annotation
    except Exception:
        session.rollback()
        raise
