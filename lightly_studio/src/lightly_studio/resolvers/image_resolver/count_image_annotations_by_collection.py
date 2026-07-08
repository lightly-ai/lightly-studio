"""Count image-scoped annotation label totals and filtered counts."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def count_image_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific image collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of (label_name, current_count, total_count) tuples.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).
    """
    # Resolve any embedding-plot region selection to concrete sample ids on the filter before the
    # query is built (the point-in-polygon test needs the session, which `apply` lacks).
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )
    total_counts = _get_total_counts(
        session=session,
        collection_id=collection_id,
        annotation_type=annotation_type,
    )
    current_counts = _get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_type=annotation_type,
    )

    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]


def _get_total_counts(
    session: Session,
    collection_id: UUID,
    annotation_type: AnnotationType | None = None,
) -> dict[str, int]:
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
    )

    if annotation_type is not None:
        total_counts_query = total_counts_query.where(
            col(AnnotationBaseTable.annotation_type) == annotation_type
        )

    total_counts_query = total_counts_query.group_by(
        AnnotationLabelTable.annotation_label_name
    ).order_by(col(AnnotationLabelTable.annotation_label_name).asc())

    return {row[0]: row[1] for row in session.exec(total_counts_query).all()}


def _get_current_counts(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None = None,
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

    if annotation_type is not None:
        filtered_query = filtered_query.where(
            col(AnnotationBaseTable.annotation_type) == annotation_type
        )

    if image_filter is not None:
        filtered_query = image_filter.apply(filtered_query)

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    rows = session.exec(filtered_query).all()
    return {row[0]: row[1] for row in rows}
