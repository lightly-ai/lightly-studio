"""Get annotation label by ID functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_by_id(session: Session, label_id: UUID) -> AnnotationLabelTable | None:
    """Retrieve a single annotation label by ID.

    Args:
        session (Session): The database session used to execute the query.
        label_id (UUID): The unique identifier of the annotation label to get.

    Returns:
        AnnotationLabelTable | None: The annotation label if found, or None.
    """
    return session.exec(
        select(AnnotationLabelTable).where(AnnotationLabelTable.annotation_label_id == label_id)
    ).one_or_none()
