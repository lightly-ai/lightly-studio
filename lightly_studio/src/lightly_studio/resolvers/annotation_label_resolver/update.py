"""Update annotation label functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)

from .get_by_id import get_by_id


def update(
    session: Session, label_id: UUID, label_data: AnnotationLabelCreate
) -> AnnotationLabelTable | None:
    """Update an existing annotation label.

    Args:
        session (Session): The database session.
        label_id (UUID): The identifier of the annotation label to update.
        label_data (AnnotationLabelCreate): The new data.

    Returns:
        AnnotationLabelTable | None: The updated annotation label if it exists,
        otherwise None.
    """
    label = get_by_id(session=session, label_id=label_id)
    if not label:
        return None

    label.annotation_label_name = label_data.annotation_label_name
    session.commit()
    session.refresh(label)
    return label
