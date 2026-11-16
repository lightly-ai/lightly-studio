"""Create annotation label functionality."""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)

from .get_by_label_name import get_by_label_name


def create(session: Session, label: AnnotationLabelCreate) -> AnnotationLabelTable:
    """Create a new annotation label in the database.

    Args:
        session (Session): The database session.
        label (AnnotationLabelCreate): The annotation label data to be created.

    Returns:
        AnnotationLabelTable: The newly created annotation label record.

    Raises:
        IntegrityError: If the dataset already has a label with the same name.
    """
    if get_by_label_name(
        session=session, dataset_id=label.dataset_id, label_name=label.annotation_label_name
    ):
        raise IntegrityError(
            statement=None, params=None, orig=Exception("Annotation label already exists")
        )
    db_label = AnnotationLabelTable.model_validate(label)
    session.add(db_label)
    session.commit()
    session.refresh(db_label)
    return db_label
