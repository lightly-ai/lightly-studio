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
    """
    return annotation_resolver.update_segmentation_mask(
        session=session,
        annotation_id=annotation_id,
        segmentation_mask=segmentation_mask,
    )
