"""Resolver for getting adjacent video frames for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjancentResultView
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter


def get_adjacent_video_frames(
    session: Session,
    sample_id: UUID,
    filters: VideoFrameFilter,
) -> AdjancentResultView:
    """Get the adjacent video frames for a given sample ID."""
    collection_id = filters.sample_filter.collection_id if filters.sample_filter else None
    if collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")

    base_query = _base_query()

    return _build_query(
        query=base_query,
        session=session,
        sample_id=sample_id,
        filters=filters,
    )


def _base_query(ordering_expression: Any | None = None) -> Select[Any]:
    ordering_expression = ordering_expression or [
        col(VideoTable.file_path_abs).asc(),
        col(VideoFrameTable.frame_number).asc(),
    ]

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
    )


def _build_query(
    query: Any,
    session: Session,
    sample_id: UUID,
    filters: VideoFrameFilter,
) -> AdjancentResultView:
    samples_query = query.join(VideoFrameTable.sample)

    if filters:
        samples_query = filters.apply(samples_query)

    adjacents_subquery = samples_query.subquery("adjacent_video_frames")
    total_count = session.exec(select(func.count()).select_from(adjacents_subquery)).one()

    adjacency_row = session.exec(
        select(
            adjacents_subquery.c.previous_sample_id,
            adjacents_subquery.c.sample_id,
            adjacents_subquery.c.next_sample_id,
            adjacents_subquery.c.row_number,
        ).where(adjacents_subquery.c.sample_id == sample_id)
    ).first()

    if adjacency_row is None:
        return AdjancentResultView(
            previous_sample_id=None,
            sample_id=sample_id,
            next_sample_id=None,
            current_sample_position=None,
            total_count=total_count,
        )

    previous_sample_id, sample_id_row, next_sample_id, row_number = adjacency_row

    current_sample_position = int(row_number) if row_number is not None else None
    return AdjancentResultView(
        previous_sample_id=previous_sample_id,
        sample_id=sample_id_row,
        next_sample_id=next_sample_id,
        current_sample_position=current_sample_position,
        total_count=total_count,
    )
