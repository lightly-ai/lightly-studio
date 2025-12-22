"""Count video frames annotations."""

from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_annotations_counter_filter import (
    VideoFrameAnnotationsCounterFilter,
)
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)


def count_video_frames_annotations(
    session: Session,
    collection_id: UUID,
    filters: Optional[VideoFrameAnnotationsCounterFilter] = None,
) -> List[CountAnnotationsView]:
    """Count the annotations by video frames."""
    unfiltered_query = (
        _build_base_query(collection_id=collection_id, count_column_name="total")
        .group_by(col(AnnotationBaseTable.annotation_label_id))
        .subquery("unfiltered")
    )

    filtered_query = _build_base_query(
        collection_id=collection_id, count_column_name="filtered_count"
    )

    if filters:
        filtered_query = filters.apply(filtered_query)

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

    return [
        CountAnnotationsView(
            label_name=row["label"],
            total_count=row["total"],
            current_count=row["filtered_count"],
        )
        for row in rows
    ]


def _build_base_query(collection_id: UUID, count_column_name: str) -> Select[Tuple[Any, int]]:
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
