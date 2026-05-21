"""Count image-scoped annotation label totals and filtered counts."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter


def count_image_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
) -> list[tuple[UUID, str, int, int]]:
    """Count annotations for a specific image collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of
    (annotation_collection_id, label_name, current_count, total_count) tuples.
    """
    total_counts = _get_total_counts(session=session, collection_id=collection_id)
    current_counts = _get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )

    return [
        (
            annotation_collection_id,
            label_name,
            current_counts.get((annotation_collection_id, label_name), 0),
            total_count,
        )
        for (annotation_collection_id, label_name), total_count in total_counts.items()
    ]


def _get_total_counts(
    session: Session,
    collection_id: UUID,
) -> dict[tuple[UUID, str], int]:
    """Returns total annotation counts per label for the collection."""
    annotation_sample = aliased(SampleTable)
    total_counts_query = (
        select(
            annotation_sample.collection_id,
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.sample_id)).label("total_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            annotation_sample,
            col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
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
        .group_by(
            annotation_sample.collection_id,
            AnnotationLabelTable.annotation_label_name,
        )
        .order_by(
            col(annotation_sample.collection_id).asc(),
            col(AnnotationLabelTable.annotation_label_name).asc(),
        )
    )

    return {(row[0], row[1]): row[2] for row in session.exec(total_counts_query).all()}


def _get_current_counts(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
) -> dict[tuple[UUID, str], int]:
    """Returns filtered annotation counts per label for the collection."""
    annotation_sample = aliased(SampleTable)
    filtered_query = (
        select(
            annotation_sample.collection_id,
            AnnotationLabelTable.annotation_label_name,
            func.count(col(AnnotationBaseTable.sample_id)).label("current_count"),
        )
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            annotation_sample,
            col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
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
    filtered_query = filtered_query.group_by(
        annotation_sample.collection_id,
        AnnotationLabelTable.annotation_label_name,
    ).order_by(
        col(annotation_sample.collection_id).asc(),
        col(AnnotationLabelTable.annotation_label_name).asc(),
    )

    rows = session.exec(filtered_query).all()
    return {(row[0], row[1]): row[2] for row in rows}
