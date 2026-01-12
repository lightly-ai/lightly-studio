"""Handler for database operations related to annotations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.type_definitions import QueryType


def count_annotations_by_collection(  # noqa: PLR0913 // FIXME: refactor to use proper pydantic
    session: Session,
    collection_id: UUID,
    filtered_labels: list[str] | None = None,
    min_width: int | None = None,
    max_width: int | None = None,
    min_height: int | None = None,
    max_height: int | None = None,
    tag_ids: list[UUID] | None = None,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific collection.

    Annotations for a specific collection are grouped by annotation
    label name and counted for total and filtered.
    Returns a list of (label_name, current_count, total_count) tuples.
    """
    # TODO(Igor, 01/2026): Use _CountFilters as the input argument to simplify this API.
    total_counts = _get_total_counts(session=session, collection_id=collection_id)
    filters = _CountFilters(
        collection_id=collection_id,
        filtered_labels=filtered_labels,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        tag_ids=tag_ids,
    )
    current_counts = _get_current_counts(session=session, filters=filters)

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


@dataclass(frozen=True)
class _CountFilters:
    collection_id: UUID
    filtered_labels: list[str] | None
    min_width: int | None
    max_width: int | None
    min_height: int | None
    max_height: int | None
    tag_ids: list[UUID] | None


def _get_current_counts(session: Session, filters: _CountFilters) -> dict[str, int]:
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
        .where(SampleTable.collection_id == filters.collection_id)
    )

    filtered_query = _apply_dimension_filters(
        query=filtered_query,
        min_width=filters.min_width,
        max_width=filters.max_width,
        min_height=filters.min_height,
        max_height=filters.max_height,
    )

    # Add label filter if specified
    if filters.filtered_labels:
        filtered_query = filtered_query.where(
            col(ImageTable.sample_id).in_(
                select(ImageTable.sample_id)
                .join(
                    AnnotationBaseTable,
                    col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
                )
                .join(
                    AnnotationLabelTable,
                    col(AnnotationBaseTable.annotation_label_id)
                    == col(AnnotationLabelTable.annotation_label_id),
                )
                .where(col(AnnotationLabelTable.annotation_label_name).in_(filters.filtered_labels))
            )
        )

    # filter by tag_ids
    if filters.tag_ids:
        filtered_query = (
            filtered_query.join(AnnotationBaseTable.tags)
            .where(AnnotationBaseTable.tags.any(col(TagTable.tag_id).in_(filters.tag_ids)))
            .distinct()
        )

    # Group by label name and sort
    filtered_query = filtered_query.group_by(AnnotationLabelTable.annotation_label_name).order_by(
        col(AnnotationLabelTable.annotation_label_name).asc()
    )

    rows = session.exec(filtered_query).all()
    return {row[0]: row[1] for row in rows}


def _apply_dimension_filters(
    query: QueryType,
    min_width: int | None,
    max_width: int | None,
    min_height: int | None,
    max_height: int | None,
) -> QueryType:
    if min_width is not None:
        query = query.where(ImageTable.width >= min_width)
    if max_width is not None:
        query = query.where(ImageTable.width <= max_width)
    if min_height is not None:
        query = query.where(ImageTable.height >= min_height)
    if max_height is not None:
        query = query.where(ImageTable.height <= max_height)
    return query
