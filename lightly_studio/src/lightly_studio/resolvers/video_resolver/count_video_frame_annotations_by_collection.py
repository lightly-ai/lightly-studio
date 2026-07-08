"""Count video frame annotations by video collection."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


class CountAnnotationsView(BaseModel):
    """Count annotations view."""

    label_name: str
    total_count: int
    current_count: int


def count_video_frame_annotations_by_video_collection(
    session: Session,
    collection_id: UUID,
    filters: Optional[VideoFilter] = None,
    annotation_type: Optional[AnnotationType] = None,
) -> list[CountAnnotationsView]:
    """Count the annotations by video frames.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).
    """
    unfiltered_query = (
        _build_base_query(
            collection_id=collection_id,
            count_column_name="total",
            annotation_type=annotation_type,
        )
        .group_by(col(AnnotationBaseTable.annotation_label_id))
        .subquery("unfiltered")
    )
    filtered_query = _build_base_query(
        collection_id=collection_id,
        count_column_name="filtered_count",
        annotation_type=annotation_type,
    )

    if filters is not None:
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
            label_name=row["label"], total_count=row["total"], current_count=row["filtered_count"]
        )
        for row in rows
    ]


def _build_base_query(
    collection_id: UUID,
    count_column_name: str,
    annotation_type: Optional[AnnotationType] = None,
) -> Select[tuple[Any, int]]:
    query: Select[tuple[Any, int]] = (
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

    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)

    return query
