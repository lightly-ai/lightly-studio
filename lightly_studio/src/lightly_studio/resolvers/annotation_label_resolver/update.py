"""Update annotation label functionality."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)

from .get_by_id import get_by_id
from .get_by_label_name import get_by_label_name


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

    Raises:
        IntegrityError: If another label of the dataset has the new name.
    """
    label = get_by_id(session=session, label_id=label_id)
    if not label:
        return None

    conflicting_label = get_by_label_name(
        session=session,
        dataset_id=label.dataset_id,
        label_name=label_data.annotation_label_name,
    )
    if conflicting_label and conflicting_label.annotation_label_id != label_id:
        raise IntegrityError(
            statement=None, params=None, orig=Exception("Annotation label already exists")
        )

    label.annotation_label_name = label_data.annotation_label_name
    session.commit()
    session.refresh(label)
    return label
