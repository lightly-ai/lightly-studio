"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable


def count_annotations_by_dataset(  # noqa: PLR0913 // FIXME: refactor to use proper pydantic
    session: Session,
    dataset_id: UUID,
    filtered_labels: list[str] | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
    min_height: int | None = None,
    max_height: int | None = None,
    tag_ids: list[UUID] | None = None,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific dataset.

    Annotations for a specific dataset are grouped by annotation
    label name and counted for total and filtered.
    """
    # Query for total counts (unfiltered)
    total_counts_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.annotation_id)).label("total_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(SampleTable.dataset_id == dataset_id)
        .group_by(AnnotationLabelTable.annotation_label_name)
        .order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    )

    total_counts = {row[0]: row[1] for row in session.exec(total_counts_query).all()}

    # Build filtered query for current counts
    filtered_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.annotation_id)).label("current_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
        )
        .where(SampleTable.dataset_id == dataset_id)
    )

    # Add dimension filters
    if min_width is not None:
        filtered_query = filtered_query.where(SampleTable.width >= min_width)
    if max_width is not None:
        filtered_query = filtered_query.where(SampleTable.width <= max_width)
    if min_height is not None:
        filtered_query = filtered_query.where(SampleTable.height >= min_height)
    if max_height is not None:
        filtered_query = filtered_query.where(SampleTable.height <= max_height)

    # Add label filter if specified
    if filtered_labels:
        filtered_query = filtered_query.where(
            col(SampleTable.sample_id).in_(
                select(SampleTable.sample_id)
                .join(
                    AnnotationBaseTable,
                    col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id),
                )
                .join(
                    AnnotationLabelTable,
                    col(AnnotationBaseTable.annotation_label_id)
                    == col(AnnotationLabelTable.annotation_label_id),
                )
                .where(col(AnnotationLabelTable.annotation_label_name).in_(filtered_labels))
            )
        )

    # filter by tag_ids
    if tag_ids:
        filtered_query = (
            filtered_query.join(AnnotationBaseTable.tags)
            .where(AnnotationBaseTable.tags.any(col(TagTable.tag_id).in_(tag_ids)))
            .distinct()
        )

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    _rows = session.exec(filtered_query).all()

    current_counts = {row[0]: row[1] for row in _rows}

    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]
