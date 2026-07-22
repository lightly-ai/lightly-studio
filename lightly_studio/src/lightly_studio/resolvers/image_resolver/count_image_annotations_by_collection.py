"""Count image-scoped annotation label totals and filtered counts."""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


class AnnotationCountMode(str, Enum):
    """Controls what the annotation count represents."""

    OBJECTS = "objects"
    SAMPLES = "samples"


def count_image_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific image collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of (label_name, current_count, total_count) tuples.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).

    When ``count_mode`` is ``OBJECTS`` (default), each annotation row is counted
    individually.  When ``count_mode`` is ``SAMPLES``, the count reflects the
    number of distinct parent samples that carry at least one matching annotation,
    so a sample with multiple annotations of the same label is counted only once.

    When a subset of annotation source collections is selected (via the filter's
    ``annotations_filter.collection_ids``), both the total and filtered counts are
    restricted to those sources. Annotations from unselected sources are excluded
    from the total as well, so the total never counts labels the current view does
    not care about (e.g. viewing a single source shows "2 of 2", not "2 of 4").
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
    annotation_collection_ids = (
        sample_filter.annotations_filter.collection_ids
        if sample_filter is not None and sample_filter.annotations_filter is not None
        else None
    )
    total_counts = _get_total_counts(
        session=session,
        collection_id=collection_id,
        annotation_type=annotation_type,
        count_mode=count_mode,
        annotation_collection_ids=annotation_collection_ids,
    )
    current_counts = _get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )

    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]


def _build_count_expression(count_mode: AnnotationCountMode) -> ColumnElement[int]:
    if count_mode == AnnotationCountMode.SAMPLES:
        return func.count(func.distinct(col(AnnotationBaseTable.parent_sample_id)))
    return func.count(col(AnnotationBaseTable.sample_id))


def _restrict_to_annotation_sources(
    query: Select[tuple[Any, int]],
    annotation_collection_ids: list[UUID],
) -> Select[tuple[Any, int]]:
    """Restrict the counted annotations to the given source collections.

    The annotation's own sample (aliased to avoid clashing with the image sample
    joined by the caller) carries its collection id.
    """
    annotation_sample = aliased(SampleTable)
    return query.join(
        annotation_sample,
        col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id),
    ).where(
        db_array.in_array(
            column=col(annotation_sample.collection_id),
            values=annotation_collection_ids,
        )
    )


def _get_total_counts(
    session: Session,
    collection_id: UUID,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
    annotation_collection_ids: list[UUID] | None = None,
) -> dict[str, int]:
    """Returns total annotation counts per label for the collection."""
    total_counts_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            _build_count_expression(count_mode).label("total_count"),
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

    if annotation_collection_ids:
        total_counts_query = _restrict_to_annotation_sources(
            total_counts_query, annotation_collection_ids
        )

    total_counts_query = total_counts_query.group_by(
        AnnotationLabelTable.annotation_label_name
    ).order_by(col(AnnotationLabelTable.annotation_label_name).asc())

    return {row[0]: row[1] for row in session.exec(total_counts_query).all()}


def _get_current_counts(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
    annotation_type: AnnotationType | None = None,
    annotation_collection_ids: list[UUID] | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> dict[str, int]:
    """Returns filtered annotation counts per label for the collection."""
    filtered_query = (
        select(
            AnnotationLabelTable.annotation_label_name,
            _build_count_expression(count_mode).label("current_count"),
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

    # Restrict the counted annotations to the selected source collections.
    if annotation_collection_ids:
        filtered_query = _restrict_to_annotation_sources(filtered_query, annotation_collection_ids)

    if image_filter is not None:
        filtered_query = image_filter.apply(filtered_query)

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    rows = session.exec(filtered_query).all()
    return {row[0]: row[1] for row in rows}
