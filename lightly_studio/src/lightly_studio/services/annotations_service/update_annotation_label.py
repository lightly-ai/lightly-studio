"""Update the label of an annotation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
)


def update_annotation_label(
    session: Session, annotation_id: UUID, root_dataset_id: UUID, label_name: str
) -> AnnotationBaseTable:
    """Update the label of an annotation.

    Args:
        session: Database session for executing the operation.
        annotation_id: UUID of the annotation to update.
        root_dataset_id: The root dataset ID to which the label belongs.
        label_name: New label to assign to the annotation.

    Returns:
        The updated annotation with the new label assigned.

    """
    annotation_label = annotation_label_resolver.get_by_label_name(
        session=session,
        root_dataset_id=root_dataset_id,
        label_name=label_name,
    )

    if not annotation_label:
        annotation_label = annotation_label_resolver.create(
            session=session,
            label=AnnotationLabelCreate(annotation_label_name=label_name),
        )

    return annotation_resolver.update_annotation_label(
        session=session,
        annotation_id=annotation_id,
        annotation_label_id=annotation_label.annotation_label_id,
    )
