"""Update the bounding box of an annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import (
    annotation_resolver,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates


def update_annotation_bounding_box(
    session: Session, annotation_id: UUID, bounding_box: BoundingBoxCoordinates
) -> AnnotationBaseTable:
    """Update the bounding box of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        bounding_box: New bounding box coordinates to assign to the annotation.

    Returns:
        The updated annotation with the new bounding box assigned.

    """
    return annotation_resolver.update_bounding_box(
        session,
        annotation_id,
        bounding_box,
    )
