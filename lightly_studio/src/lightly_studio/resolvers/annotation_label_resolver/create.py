"""Create annotation label functionality."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)


def create(session: Session, label: AnnotationLabelCreate) -> AnnotationLabelTable:
    """Create a new annotation label in the database.

    Args:
        session (Session): The database session.
        label (AnnotationLabelCreate): The annotation label data to be created.

    Returns:
        AnnotationLabelTable: The newly created annotation label record.
    """
    db_label = AnnotationLabelTable.model_validate(label)
    session.add(db_label)
    session.commit()
    session.refresh(db_label)
    return db_label
