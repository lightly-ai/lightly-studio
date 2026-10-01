"""Count video annotations by video collection."""

from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import union_all
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
    """Count annotations attached to videos, including frame and direct video labels.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).
    """
    label_video_pairs = _build_label_video_pairs_subquery(
        collection_id=collection_id, annotation_type=annotation_type
    )

    unfiltered_query = (
        select(
            label_video_pairs.c.label_id,
            func.count(func.distinct(label_video_pairs.c.video_id)).label("total"),
        )
        .select_from(label_video_pairs)
        .group_by(label_video_pairs.c.label_id)
        .subquery("unfiltered")
    )

    filtered_pairs_query: Select[tuple[Any, Any]] = (
        select(
            label_video_pairs.c.label_id,
            label_video_pairs.c.video_id,
        )
        .select_from(label_video_pairs)
        .join(VideoTable, col(VideoTable.sample_id) == label_video_pairs.c.video_id)
        .join(SampleTable, col(SampleTable.sample_id) == col(VideoTable.sample_id))
    )
    if filters is not None:
        filtered_pairs_query = filters.apply(filtered_pairs_query)

    filtered_pairs_subquery = filtered_pairs_query.subquery("filtered_pairs")
    filtered_subquery = (
        select(
            filtered_pairs_subquery.c.label_id,
            func.count(func.distinct(filtered_pairs_subquery.c.video_id)).label("filtered_count"),
        )
        .select_from(filtered_pairs_subquery)
        .group_by(filtered_pairs_subquery.c.label_id)
        .subquery("filtered")
    )

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


def _build_label_video_pairs_subquery(
    collection_id: UUID, annotation_type: Optional[AnnotationType] = None
) -> Any:
    """Return (label_id, video_id) pairs from frame and direct video annotations.

    When ``annotation_type`` is provided, only annotations of that type are considered.
    """
    frame_pairs: Select[tuple[Any, Any]] = (
        select(
            col(AnnotationBaseTable.annotation_label_id).label("label_id"),
            col(VideoTable.sample_id).label("video_id"),
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
    video_pairs: Select[tuple[Any, Any]] = (
        select(
            col(AnnotationBaseTable.annotation_label_id).label("label_id"),
            col(VideoTable.sample_id).label("video_id"),
        )
        .select_from(AnnotationBaseTable)
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(VideoTable, col(VideoTable.sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if annotation_type is not None:
        frame_pairs = frame_pairs.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
        video_pairs = video_pairs.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    return union_all(frame_pairs, video_pairs).subquery("label_video_pairs")
