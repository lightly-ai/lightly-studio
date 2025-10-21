"""Handler for database operations related to annotation labels."""

from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.annotation_label import (
    AnnotationLabelTable,
)


def get_by_label_name(session: Session, label_name: str) -> AnnotationLabelTable | None:
    """Retrieve a single annotation label by its name.

    Args:
        session: The database session to use for the query.
        label_name: The name of the annotation label to retrieve.

    Returns:
        The AnnotationLabelTable instance if found, None otherwise.
    """
    return session.exec(
        select(AnnotationLabelTable).where(AnnotationLabelTable.annotation_label_name == label_name)
    ).one_or_none()
