"""Count the annotations of each annotation label."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable


def get_annotation_counts(session: Session, dataset_id: UUID) -> dict[UUID, int]:
    """Count the annotations of each annotation label of a dataset.

    The count includes all annotation types and sample types, for example annotations
    of images and of video frames.

    Args:
        session: The database session.
        dataset_id: The dataset ID to which the labels belong.

    Returns:
        A mapping from each annotation label ID to its number of annotations. Labels
        without annotations map to 0.
    """
    rows = session.exec(
        select(
            AnnotationLabelTable.annotation_label_id,
            func.count(col(AnnotationBaseTable.sample_id)),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
            isouter=True,
        )
        .where(AnnotationLabelTable.dataset_id == dataset_id)
        .group_by(col(AnnotationLabelTable.annotation_label_id))
    ).all()
    return dict(rows)
