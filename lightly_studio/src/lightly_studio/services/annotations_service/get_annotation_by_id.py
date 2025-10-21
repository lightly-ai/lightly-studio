"""Get an annotation by its ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import (
    annotation_resolver,
)


def get_annotation_by_id(session: Session, annotation_id: UUID) -> AnnotationBaseTable:
    """Retrieve an annotation by its ID.

    Args:
        session: Database session for executing the operation.
        annotation_id: ID of the annotation to retrieve.

    Returns:
        The retrieved annotation.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation {annotation_id} not found")

    return annotation
