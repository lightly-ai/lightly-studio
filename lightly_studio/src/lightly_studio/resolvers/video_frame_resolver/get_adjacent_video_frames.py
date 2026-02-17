"""Resolver for getting adjacent video frames for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import adjacents
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter


def get_adjacent_video_frames(
    session: Session,
    sample_id: UUID,
    filters: VideoFrameFilter,
) -> AdjacentResultView | None:
    """Get the adjacent video frames for a given sample ID."""
    collection_id = filters.sample_filter.collection_id if filters.sample_filter else None
    if collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")

    base_query = _base_query()

    if filters:
        base_query = filters.apply(base_query)

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _base_query() -> Select[Any]:
    ordering_expression: tuple[ColumnElement[Any], ColumnElement[Any]] = (
        col(VideoTable.file_path_abs).asc(),
        col(VideoFrameTable.frame_number).asc(),
    )

    return (
        select(
            col(VideoFrameTable.sample_id).label("sample_id"),
            func.lag(col(VideoFrameTable.sample_id))
            .over(order_by=ordering_expression)
            .label("previous_sample_id"),
            func.lead(col(VideoFrameTable.sample_id))
            .over(order_by=ordering_expression)
            .label("next_sample_id"),
            func.row_number().over(order_by=ordering_expression).label("row_number"),
        )
        .select_from(VideoFrameTable)
        .join(VideoTable)
        .join(VideoFrameTable.sample)
    )
