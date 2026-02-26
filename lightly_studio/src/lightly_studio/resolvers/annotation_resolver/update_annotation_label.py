"""Module for handling the update of annotation labels in the database."""

from __future__ import annotations

from typing import TypeVar
from uuid import UUID

from sqlmodel import Session, SQLModel

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.resolvers import (
    annotation_resolver,
)
from lightly_studio.resolvers.annotation_resolver import annotation_helper

T = TypeVar("T", bound=SQLModel)


def update_annotation_label(
    session: Session, annotation_id: UUID, annotation_label_id: UUID
) -> AnnotationBaseTable:
    """Update the label of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        annotation_label_id: UUID of the new label to assign to the annotation.

    Returns:
        The updated annotation with the new label assigned.

    Raises:
        ValueError: If the annotation is not found.
    """
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise ValueError(f"Annotation with ID {annotation_id} not found.")
    return annotation_helper.update_annotation_object(
        session=session,
        annotation=annotation,
        fields_to_update={"annotation_label_id": annotation_label_id},
    )
