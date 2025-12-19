"""Create annotation."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.resolvers import annotation_resolver


class AnnotationCreateParams(BaseModel):
    """Input model for create annotation service."""

    annotation_label_id: UUID
    annotation_type: AnnotationType
    collection_id: UUID
    parent_sample_id: UUID

    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None

    segmentation_mask: list[int] | None = None


def create_annotation(session: Session, annotation: AnnotationCreateParams) -> AnnotationBaseTable:
    """Create a new annotation.

    Args:
        session: Database session for executing the operation.
        annotation: Annotation data to create.

    Returns:
        The retrieved annotation.
    """
    annotation_create = AnnotationCreate(
        **annotation.model_dump(),
    )
    new_annotation_ids = annotation_resolver.create_many(
        session=session,
        parent_collection_id=annotation.collection_id,
        annotations=[annotation_create],
    )

    if not new_annotation_ids:
        raise ValueError("Failed to create annotation.")

    created_annotation = annotation_resolver.get_by_id(
        session=session,
        annotation_id=new_annotation_ids[0],
    )

    if created_annotation is None:
        raise ValueError(f"Failed to create annotation: {annotation}")

    return created_annotation
