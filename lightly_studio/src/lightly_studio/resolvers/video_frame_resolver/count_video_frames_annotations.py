"""Count video frames annotations."""

from typing import Any, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import false
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

NO_ANNOTATIONS_LABEL = "No annotations"


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

    include_no_annotations = filters.include_no_annotations if filters else None
    labels_filter_active = bool(filters and filters.annotations_labels)
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
            label_name=row["label"],
            total_count=row["total"],
            current_count=row["filtered_count"],
        )
        for row in rows
    ]

    annotated_frame_ids_subquery = (
        select(AnnotationBaseTable.parent_sample_id).select_from(AnnotationBaseTable).distinct()
    )

    total_no_annotations_query = (
        select(func.count())
        .select_from(VideoFrameTable)
        .join(SampleTable, col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
        .where(~col(VideoFrameTable.sample_id).in_(annotated_frame_ids_subquery))
    )
    total_no_annotations = session.exec(total_no_annotations_query).one()

    current_no_annotations = 0
    if not (filters and filters.annotations_labels and not include_no_annotations):
        current_no_annotations_query = (
            select(func.count())
            .select_from(VideoFrameTable)
            .join(SampleTable, col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id))
            .where(col(SampleTable.collection_id) == collection_id)
            .where(~col(VideoFrameTable.sample_id).in_(annotated_frame_ids_subquery))
        )
        if filters and filters.video_filter:
            video_filter = filters.video_filter.model_copy(update={"sample_filter": None})
            if filters.video_filter.sample_filter:
                video_filter.sample_filter = filters.video_filter.sample_filter.model_copy(
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
