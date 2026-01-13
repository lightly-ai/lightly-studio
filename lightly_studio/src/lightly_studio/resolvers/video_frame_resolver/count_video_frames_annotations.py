"""Count video frames annotations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.sample_resolver.sample_filter import AnnotationFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_annotations_counter_filter import (
    VideoFrameAnnotationsCounterFilter,
)
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)

NO_ANNOTATIONS_LABEL = "No annotations"


def count_video_frames_annotations(
    session: Session,
    collection_id: UUID,
    filters: VideoFrameAnnotationsCounterFilter | None = None,
) -> list[CountAnnotationsView]:
    """Count the annotations by video frames."""
    unfiltered_query = (
        _build_base_query(collection_id=collection_id, count_column_name="total")
        .group_by(col(AnnotationBaseTable.annotation_label_id))
        .subquery("unfiltered")
    )

    filtered_query = _build_base_query(
        collection_id=collection_id, count_column_name="filtered_count"
    )

    annotation_filter = _build_annotation_filter(session=session, filters=filters)
    if annotation_filter:
        filtered_query = annotation_filter.apply_to_samples(
            query=filtered_query, sample_id_column=col(VideoFrameTable.sample_id)
        )
    if filters:
        filtered_query = filters.apply_video_filter(filtered_query)

    filtered_subquery = filtered_query.group_by(
        col(AnnotationBaseTable.annotation_label_id)
    ).subquery("filtered")

    final_query: Select[Any] = (
        select(
            col(AnnotationLabelTable.annotation_label_name).label("label"),
            col(unfiltered_query.c.total).label("total"),
            func.coalesce(filtered_subquery.c.filtered_count, 0).label("filtered_count"),
        )
        .select_from(AnnotationLabelTable)
        .join(
            unfiltered_query,
            unfiltered_query.c.label_id == col(AnnotationLabelTable.annotation_label_id),
        )
        .outerjoin(
            filtered_subquery,
            filtered_subquery.c.label_id == col(AnnotationLabelTable.annotation_label_id),
        )
        .order_by(asc(AnnotationLabelTable.annotation_label_name))
    )

    rows = session.execute(final_query).mappings().all()

    results = [
        CountAnnotationsView(
            label_name=row["label"],
            total_count=row["total"],
            current_count=row["filtered_count"],
        )
        for row in rows
    ]

    annotated_frame_ids_subquery = (
        select(AnnotationBaseTable.parent_sample_id).select_from(AnnotationBaseTable).distinct()
    )

    if filters and filters.include_unannotated_samples:
        # TODO(Igor, 01/2026): Remove this guard once the frontend supports unannotated counts.
        total_unannotated_query = (
            select(func.count())
            .select_from(VideoFrameTable)
            .join(SampleTable, col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id))
            .where(col(SampleTable.collection_id) == collection_id)
            .where(~col(VideoFrameTable.sample_id).in_(annotated_frame_ids_subquery))
        )
        total_unannotated_samples = session.exec(total_unannotated_query).one()

        current_unannotated_samples = 0
        if not (annotation_filter and not annotation_filter.allows_unannotated()):
            current_unannotated_query = (
                select(func.count())
                .select_from(VideoFrameTable)
                .join(SampleTable, col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id))
                .where(col(SampleTable.collection_id) == collection_id)
                .where(~col(VideoFrameTable.sample_id).in_(annotated_frame_ids_subquery))
            )
            if filters.video_filter:
                video_filter = filters.video_filter.without_annotation_filters()
                current_unannotated_query = video_filter.apply(current_unannotated_query)

            current_unannotated_samples = session.exec(current_unannotated_query).one()

        results.append(
            CountAnnotationsView(
                label_name=NO_ANNOTATIONS_LABEL,
                total_count=total_unannotated_samples,
                current_count=current_unannotated_samples,
            )
        )
    return results


def _build_base_query(collection_id: UUID, count_column_name: str) -> Select[tuple[Any, int]]:
    """Build the base annotations count query for a collection."""
    return (
        select(
            col(AnnotationBaseTable.annotation_label_id).label("label_id"),
            func.count(col(AnnotationBaseTable.annotation_label_id)).label(count_column_name),
        )
        .select_from(AnnotationBaseTable)
        .join(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )


def _build_annotation_filter(
    session: Session, filters: VideoFrameAnnotationsCounterFilter | None
) -> AnnotationFilter | None:
    """Build an AnnotationFilter from counter filters."""
    if not filters:
        return None

    annotation_label_ids = _resolve_annotation_label_ids(
        session=session, annotation_label_names=filters.annotations_labels
    )
    return AnnotationFilter.from_params(
        annotation_label_ids=annotation_label_ids,
        include_unannotated_samples=filters.include_unannotated_samples,
        preserve_empty_label_ids=True,
    )


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
