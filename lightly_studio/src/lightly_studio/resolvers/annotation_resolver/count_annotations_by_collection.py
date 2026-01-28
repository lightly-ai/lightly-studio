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
from lightly_studio.resolvers.annotation_filter import AnnotationFilter
from lightly_studio.type_definitions import QueryType

NO_ANNOTATIONS_LABEL = "No annotations"


def count_annotations_by_collection(  # noqa: PLR0913 // FIXME: refactor to use proper pydantic
    session: Session,
    collection_id: UUID,
    filtered_labels: list[str] | None = None,
    include_unannotated_samples: bool | None = None,
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
    # TODO(Igor, 01/2026): Keep name-based filtering here; refactor after API shape settles.
    filtered_label_ids = _resolve_annotation_label_ids(
        session=session, annotation_label_names=filtered_labels
    )
    annotation_filter = AnnotationFilter.from_params(
        annotation_label_ids=filtered_label_ids,
        include_unannotated_samples=include_unannotated_samples,
        preserve_empty_label_ids=True,
    )
    filters = _CountFilters(
        collection_id=collection_id,
        annotation_filter=annotation_filter,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        tag_ids=tag_ids,
    )
    current_counts = _get_current_counts(session=session, filters=filters)
    results = [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]
    if include_unannotated_samples:
        # TODO(Igor, 01/2026): Remove this guard once the frontend supports unannotated counts.
        total_unannotated_samples = _count_total_samples_without_annotations(
            session=session, collection_id=collection_id
        )
        current_unannotated_samples = _count_filtered_samples_without_annotations(
            session=session, filters=filters
        )
        results.append(
            (NO_ANNOTATIONS_LABEL, current_unannotated_samples, total_unannotated_samples)
        )
    return results


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
    annotation_filter: AnnotationFilter | None
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

    if filters.annotation_filter:
        filtered_query = filters.annotation_filter.apply_to_samples(
            query=filtered_query, sample_id_column=col(ImageTable.sample_id)
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


def _count_total_samples_without_annotations(session: Session, collection_id: UUID) -> int:
    """Returns the number of samples in the collection without annotations."""
    total_no_annotations_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(
            ~col(ImageTable.sample_id).in_(select(AnnotationBaseTable.parent_sample_id).distinct())
        )
    )
    return session.exec(total_no_annotations_query).one()


def _count_filtered_samples_without_annotations(session: Session, filters: _CountFilters) -> int:
    """Returns the number of samples without annotations after applying filters."""
    if filters.tag_ids or (
        filters.annotation_filter and not filters.annotation_filter.allows_unannotated()
    ):
        return 0

    current_no_annotations_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(col(SampleTable.collection_id) == filters.collection_id)
        .where(
            ~col(ImageTable.sample_id).in_(select(AnnotationBaseTable.parent_sample_id).distinct())
        )
    )
    current_no_annotations_query = _apply_dimension_filters(
        query=current_no_annotations_query,
        min_width=filters.min_width,
        max_width=filters.max_width,
        min_height=filters.min_height,
        max_height=filters.max_height,
    )
    return session.exec(current_no_annotations_query).one()


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


def _resolve_annotation_label_ids(
    session: Session, annotation_label_names: list[str] | None
) -> list[UUID] | None:
    """Return label IDs for the provided label names."""
    if annotation_label_names is None or not annotation_label_names:
        return None
    rows = session.exec(
        select(AnnotationLabelTable.annotation_label_id).where(
            col(AnnotationLabelTable.annotation_label_name).in_(annotation_label_names)
        )
    ).all()
    return list(rows)
