"""Get all annotation labels functionality."""

from __future__ import annotations

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_all(session: Session) -> list[AnnotationLabelTable]:
    """Retrieve all annotation labels.

    Args:
        session (Session): The database session.

    Returns:
        list[AnnotationLabelTable]: A list of annotation labels.
    """
    labels = session.exec(
        select(AnnotationLabelTable).order_by(col(AnnotationLabelTable.created_at).asc())
    ).all()
    return list(labels) if labels else []


def get_all_sorted_alphabetically(session: Session) -> list[AnnotationLabelTable]:
    """Retrieve all annotation labels sorted alphabetically.

    Args:
        session (Session): The database session.

    Returns:
        list[AnnotationLabelTable]: A list of annotation labels.
    """
    labels = session.exec(
        select(AnnotationLabelTable).order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    ).all()
    return list(labels) if labels else []
