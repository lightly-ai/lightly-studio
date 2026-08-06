"""Get annotation labels with annotation counts functionality."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import (
    AnnotationLabelTable,
    AnnotationLabelWithCountView,
)


def get_all_with_counts(
    session: Session,
    dataset_id: UUID,
) -> list[AnnotationLabelWithCountView]:
    """Retrieve all annotation labels and their annotation counts.

    Args:
        session: The database session.
        dataset_id: The dataset ID to which the labels belong.

    Returns:
        Annotation labels ordered by creation time, including zero-count labels.
    """
    rows = session.exec(
        select(
            AnnotationLabelTable,
            func.count(col(AnnotationBaseTable.sample_id)).label("annotation_count"),
        )
        .outerjoin(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .where(AnnotationLabelTable.dataset_id == dataset_id)
        .group_by(
            col(AnnotationLabelTable.annotation_label_id),
            col(AnnotationLabelTable.dataset_id),
            col(AnnotationLabelTable.annotation_label_name),
            col(AnnotationLabelTable.created_at),
        )
        .order_by(col(AnnotationLabelTable.created_at).asc())
    ).all()
    return [
        AnnotationLabelWithCountView(
            annotation_label_id=label.annotation_label_id,
            dataset_id=label.dataset_id,
            annotation_label_name=label.annotation_label_name,
            created_at=label.created_at,
            annotation_count=count,
        )
        for label, count in rows
    ]
