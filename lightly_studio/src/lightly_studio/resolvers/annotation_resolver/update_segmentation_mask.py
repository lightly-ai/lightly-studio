"""Update the segmentation mask field."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotation_resolver.delete_annotation import (
    delete_evaluation_metrics,
)


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
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")

    if not annotation.segmentation_details:
        raise ValueError("Annotation type does not support segmentation mask.")

    try:
        # TODO(Malte, 07/2026): Replace eager deletion with explicit evaluation invalidation
        # once evaluation results can be recomputed or marked stale independently from updates.
        delete_evaluation_metrics(
            session=session,
            annotation_ids=[annotation.sample_id],
            parent_sample_ids=[annotation.parent_sample_id],
        )
        annotation.segmentation_details.segmentation_mask = segmentation_mask

        session.commit()
        session.refresh(annotation)
        return annotation
    except Exception:
        session.rollback()
        raise
