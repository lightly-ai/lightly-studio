"""Get all annotation labels functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_all(session: Session, dataset_id: UUID) -> list[AnnotationLabelTable]:
    """Retrieve all annotation labels.

    Args:
        session (Session): The database session.
        dataset_id (UUID): The root collection ID to to which the labels belong.

    Returns:
        list[AnnotationLabelTable]: A list of annotation labels.
    """
    labels = session.exec(
        select(AnnotationLabelTable)
        .where(AnnotationLabelTable.dataset_id == dataset_id)
        .order_by(col(AnnotationLabelTable.created_at).asc())
    ).all()
    return list(labels) if labels else []


def get_all_sorted_alphabetically(session: Session, dataset_id: UUID) -> list[AnnotationLabelTable]:
    """Retrieve all annotation labels sorted alphabetically.

    Args:
        session (Session): The database session.
        dataset_id (UUID): The root collection ID to to which the labels belong.

    Returns:
        list[AnnotationLabelTable]: A list of annotation labels.
    """
    labels = session.exec(
        select(AnnotationLabelTable)
        .where(AnnotationLabelTable.dataset_id == dataset_id)
        .order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    ).all()
    return list(labels) if labels else []
