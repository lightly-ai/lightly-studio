"""Count video frame annotations by video collection."""

from typing import Any, List, Optional, Tuple
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import false
from sqlmodel import Session, asc, col, func, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
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
    session: Session, collection_id: UUID, filters: Optional[VideoCountAnnotationsFilter] = None
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

    include_no_annotations = filters.include_no_annotations if filters else None
    labels_filter_active = bool(filters and filters.video_frames_annotations_labels)
    if include_no_annotations and not labels_filter_active:
        filtered_query = filtered_query.where(false())
    elif filters:
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
    if not (filters and filters.video_frames_annotations_labels and not include_no_annotations):
        current_no_annotations_query = (
            select(func.count())
            .select_from(VideoTable)
            .join(SampleTable, col(SampleTable.sample_id) == col(VideoTable.sample_id))
            .where(col(SampleTable.collection_id) == collection_id)
            .where(~col(VideoTable.sample_id).in_(annotated_video_ids_subquery))
        )
        if filters and filters.video_filter:
            video_filter = filters.video_filter.model_copy(
                update={"annotation_frames_label_ids": None, "include_no_annotations": None}
            )
            if video_filter.sample_filter:
                video_filter.sample_filter = video_filter.sample_filter.model_copy(
                    update={
                        "annotation_label_ids": None,
                        "include_no_annotations": None,
                    }
                )
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


def _build_base_query(collection_id: UUID, count_column_name: str) -> Select[Tuple[Any, int]]:
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
