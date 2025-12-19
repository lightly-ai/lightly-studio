"""Retrieve the minimum and maximum values of each video table field."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import Select, select
from sqlmodel import Session, col, func

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.range import FloatRange, IntRange
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import (
    VideoFieldsBoundsView,
    VideoFrameTable,
    VideoTable,
)


def get_table_fields_bounds(
    session: Session, collection_id: UUID, annotations_frames_labels_id: list[UUID] | None = None
) -> VideoFieldsBoundsView | None:
    """Find the minimum and maximum values (bounds) of the video fields.

    This includes fps, width, height, and duration. If annotation label
    filters are provided, only videos containing those annotations are
    considered.
    """
    query: Select[tuple[Any, ...]] = select(
        func.min(VideoTable.width).label("min_width"),
        func.max(VideoTable.width).label("max_width"),
        func.min(VideoTable.height).label("min_height"),
        func.max(VideoTable.height).label("max_height"),
        func.min(VideoTable.duration_s).label("min_duration_s"),
        func.max(VideoTable.duration_s).label("max_duration_s"),
        func.min(VideoTable.fps).label("min_fps"),
        func.max(VideoTable.fps).label("max_fps"),
    )

    query = query.join(SampleTable)

    if annotations_frames_labels_id:
        annotation_video_ids_subquery = (
            select(col(VideoTable.sample_id))
            .select_from(VideoTable)
            .join(VideoFrameTable)
            .join(SampleTable, col(SampleTable.sample_id) == col(VideoFrameTable.sample_id))
            .join(
                AnnotationBaseTable,
                col(AnnotationBaseTable.parent_sample_id) == col(SampleTable.sample_id),
            )
            .where(col(AnnotationBaseTable.annotation_label_id).in_(annotations_frames_labels_id))
            .distinct()
        )

        query = query.where(col(VideoTable.sample_id).in_(annotation_video_ids_subquery))

    query = query.where(col(SampleTable.collection_id) == collection_id)

    result = session.execute(query).mappings().one()

    ## If the min_width is empty, then no data is found.
    if result["min_width"] is None:
        return None

    return VideoFieldsBoundsView(
        width=IntRange(min=result["min_width"], max=result["max_width"]),
        height=IntRange(min=result["min_height"], max=result["max_height"]),
        duration_s=FloatRange(min=result["min_duration_s"], max=result["max_duration_s"]),
        fps=FloatRange(min=result["min_fps"], max=result["max_fps"]),
    )
