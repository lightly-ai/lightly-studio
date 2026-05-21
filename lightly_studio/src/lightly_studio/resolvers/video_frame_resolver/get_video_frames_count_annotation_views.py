"""Count video frames annotations."""

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)


def get_video_frames_count_annotation_views(
    session: Session,
    collection_id: UUID,
    filters: Optional[VideoFrameFilter] = None,
) -> list[CountAnnotationsView]:
    """Count the annotations by video frames."""
    unfiltered_query = (
        _build_base_query(collection_id=collection_id, count_column_name="total")
        .group_by(col("annotation_collection_id"), col("label_name"))
        .subquery("unfiltered")
    )

    filtered_query = _build_base_query(
        collection_id=collection_id, count_column_name="filtered_count"
    )

    if filters is not None:
        filtered_query = filters.apply(filtered_query)

    filtered_subquery = filtered_query.group_by(
        col("annotation_collection_id"), col("label_name")
    ).subquery("filtered")

    final_query: Select[Any] = (
        select(
            col(unfiltered_query.c.annotation_collection_id).label("annotation_collection_id"),
            col(unfiltered_query.c.label_name).label("label"),
            col(unfiltered_query.c.total).label("total"),
            func.coalesce(filtered_subquery.c.filtered_count, 0).label("filtered_count"),
        )
        .select_from(unfiltered_query)
        .outerjoin(
            filtered_subquery,
            (filtered_subquery.c.label_name == unfiltered_query.c.label_name)
            & (filtered_subquery.c.annotation_collection_id == unfiltered_query.c.annotation_collection_id),
        )
        .order_by(
            asc(unfiltered_query.c.annotation_collection_id),
            asc(unfiltered_query.c.label_name),
        )
    )

    rows = session.execute(final_query).mappings().all()

    return [
        CountAnnotationsView(
            annotation_collection_id=row["annotation_collection_id"],
            label_name=row["label"],
            total_count=row["total"],
            current_count=row["filtered_count"],
        )
        for row in rows
    ]


def _build_base_query(collection_id: UUID, count_column_name: str) -> Select[tuple[Any, int]]:
    annotation_sample = aliased(SampleTable)
    return (
        select(
            col(annotation_sample.collection_id).label("annotation_collection_id"),
            col(AnnotationLabelTable.annotation_label_name).label("label_name"),
            func.count(col(AnnotationBaseTable.annotation_label_id)).label(count_column_name),
        )
        .select_from(AnnotationBaseTable)
        .join(annotation_sample, col(annotation_sample.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(
            AnnotationLabelTable,
            col(AnnotationBaseTable.annotation_label_id) == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(SampleTable, col(VideoFrameTable.sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )
