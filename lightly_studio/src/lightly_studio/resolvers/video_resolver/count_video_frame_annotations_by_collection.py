"""Count video frame annotations by video collection."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.sample_resolver.sample_filter import AnnotationFilter
from lightly_studio.resolvers.video_resolver.video_count_annotations_filter import (
    VideoCountAnnotationsFilter,
)

NO_ANNOTATIONS_LABEL = "No annotations"


class CountAnnotationsView(BaseModel):
    """Count annotations view."""

    label_name: str
    total_count: int
    current_count: int


def count_video_frame_annotations_by_video_collection(
    session: Session, collection_id: UUID, filters: VideoCountAnnotationsFilter | None = None
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
        filtered_query = annotation_filter.apply_to_videos(filtered_query)
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
            label_name=row["label"], total_count=row["total"], current_count=row["filtered_count"]
        )
        for row in rows
    ]

    annotated_video_ids_subquery = (
        select(VideoTable.sample_id)
        .join(VideoTable.frames)
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.parent_sample_id) == VideoFrameTable.sample_id,
        )
        .distinct()
    )

    total_no_annotations_query = (
        select(func.count())
        .select_from(VideoTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(VideoTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(~col(VideoTable.sample_id).in_(annotated_video_ids_subquery))
    )
    total_no_annotations = session.exec(total_no_annotations_query).one()

    current_no_annotations = 0
    if not (annotation_filter and not annotation_filter.allows_unannotated()):
        current_no_annotations_query = (
            select(func.count())
            .select_from(VideoTable)
            .join(SampleTable, col(SampleTable.sample_id) == col(VideoTable.sample_id))
            .where(col(SampleTable.collection_id) == collection_id)
            .where(~col(VideoTable.sample_id).in_(annotated_video_ids_subquery))
        )
        if filters and filters.video_filter:
            video_filter = filters.video_filter.without_annotation_filters()
            current_no_annotations_query = video_filter.apply(current_no_annotations_query)

        current_no_annotations = session.exec(current_no_annotations_query).one()

    results.append(
        CountAnnotationsView(
            label_name=NO_ANNOTATIONS_LABEL,
            total_count=total_no_annotations,
            current_count=current_no_annotations,
        )
    )
    return results


def _build_base_query(collection_id: UUID, count_column_name: str) -> Select[tuple[Any, int]]:
    return (
        select(
            col(AnnotationBaseTable.annotation_label_id).label("label_id"),
            func.count(func.distinct(VideoTable.sample_id)).label(count_column_name),
        )
        .select_from(AnnotationBaseTable)
        .join(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(VideoFrameTable.parent_sample_id))
        .join(VideoTable, col(VideoTable.sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )


def _build_annotation_filter(
    session: Session, filters: VideoCountAnnotationsFilter | None
) -> AnnotationFilter | None:
    if not filters:
        return None

    annotation_label_ids = _resolve_annotation_label_ids(
        session=session, annotation_label_names=filters.video_frames_annotations_labels
    )
    return AnnotationFilter.from_params(
        annotation_label_ids=annotation_label_ids,
        include_no_annotations=filters.include_no_annotations,
        preserve_empty_label_ids=True,
    )


def _resolve_annotation_label_ids(
    session: Session, annotation_label_names: list[str] | None
) -> list[UUID] | None:
    if annotation_label_names is None or not annotation_label_names:
        return None
    rows = session.exec(
        select(AnnotationLabelTable.annotation_label_id).where(
            col(AnnotationLabelTable.annotation_label_name).in_(annotation_label_names)
        )
    ).all()
    return list(rows)
