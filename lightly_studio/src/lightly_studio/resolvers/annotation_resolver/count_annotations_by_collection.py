"""Handler for database operations related to annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter


def count_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of (label_name, current_count, total_count) tuples.
    """
    total_counts = _get_total_counts(session=session, collection_id=collection_id)
    current_counts = _get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )

    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]


def _get_total_counts(session: Session, collection_id: UUID) -> dict[str, int]:
    """Returns total annotation counts per label for the collection."""
    total_counts_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.sample_id)).label("total_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
        .group_by(AnnotationLabelTable.annotation_label_name)
        .order_by(col(AnnotationLabelTable.annotation_label_name).asc())
    )

    return {row[0]: row[1] for row in session.exec(total_counts_query).all()}


def _get_current_counts(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
) -> dict[str, int]:
    """Returns filtered annotation counts per label for the collection."""
    filtered_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.sample_id)).label("current_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )

    if image_filter is not None:
        filtered_query = image_filter.apply(filtered_query)

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    rows = session.exec(filtered_query).all()
    return {row[0]: row[1] for row in rows}
