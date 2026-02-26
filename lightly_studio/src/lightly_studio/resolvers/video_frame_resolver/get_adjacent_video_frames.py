"""Resolver for getting adjacent video frames for a given sample ID."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Subquery
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import adjacents, collection_resolver, similarity_utils
from lightly_studio.resolvers.video_frame_resolver.video_frame_adjacent_filter import (
    VideoFrameAdjacentFilter,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def get_adjacent_video_frames(
    session: Session,
    sample_id: UUID,
    filters: VideoFrameAdjacentFilter,
) -> AdjacentResultView | None:
    """Get the adjacent video frames for a given sample ID."""
    video_frame_filter = filters.video_frame_filter
    collection_id = (
        video_frame_filter.sample_filter.collection_id if video_frame_filter.sample_filter else None
    )
    if collection_id is None:
        raise ValueError("Collection ID must be provided in video_frame_filter.sample_filter.")

    video_filter = filters.video_filter

    video_collection_id: UUID | None = None
    if video_filter and video_filter.sample_filter and video_filter.sample_filter.collection_id:
        video_collection_id = video_filter.sample_filter.collection_id
    else:
        parent_collection = collection_resolver.get_parent_collection_id(
            session=session,
            collection_id=collection_id,
        )
        if parent_collection is not None:
            video_collection_id = parent_collection.collection_id

    if filters.video_text_embedding is not None and video_collection_id is None:
        raise ValueError("Collection ID must be resolvable when video_text_embedding is provided.")

    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=video_collection_id or collection_id,
        text_embedding=filters.video_text_embedding,
    )

    ordering_expression: list[ColumnElement[Any]] = list(_default_ordering_expression())

    if distance_expr is not None:
        ordering_expression = [distance_expr, *ordering_expression]

    base_query = _base_query(ordering_expression=ordering_expression)

    if distance_expr is not None and embedding_model_id is not None:
        base_query = similarity_utils.apply_similarity_join(
            query=base_query,
            sample_id_column=col(VideoTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    base_query = video_frame_filter.apply(base_query)

    video_ids_subquery = _video_ids_subquery(video_filter=video_filter)

    if video_ids_subquery is not None:
        base_query = base_query.where(
            col(VideoFrameTable.parent_sample_id).in_(select(video_ids_subquery.c.video_sample_id))
        )

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _base_query(ordering_expression: Iterable[ColumnElement[Any]] | None = None) -> Select[Any]:
    ordering_expression = tuple(ordering_expression or _default_ordering_expression())
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


def _default_ordering_expression() -> tuple[ColumnElement[Any], ColumnElement[Any]]:
    return (
        col(VideoTable.file_path_abs).asc(),
        col(VideoFrameTable.frame_number).asc(),
    )


def _video_ids_subquery(video_filter: VideoFilter | None) -> Subquery | None:
    if video_filter is None:
        return None

    video_ids_query: SelectOfScalar[UUID] = (
        select(col(VideoTable.sample_id).label("video_sample_id"))
        .select_from(VideoTable)
        .join(VideoTable.sample)
    )

    video_ids_query = video_filter.apply(video_ids_query)

    return video_ids_query.subquery()
