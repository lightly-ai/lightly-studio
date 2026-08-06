"""Resolver for getting adjacent videos for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers import adjacents, similarity_utils
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def get_adjacent_videos(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: VideoFilter | None = None,
    text_embedding: list[float] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent videos for a given sample ID."""
    base_query = _base_query(order_by=order_by)
    base_query = base_query.where(col(SampleTable.collection_id) == collection_id)

    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        # Similarity search overrides dataset sort (same as the video list API).
        base_query = similarity_utils.apply_similarity_join(
            query=_base_query(ordering_expression=[distance_expr]).where(
                col(SampleTable.collection_id) == collection_id
            ),
            sample_id_column=col(VideoTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    if filters:
        base_query = filters.apply(base_query)

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _window_order_columns(
    ordering_expression: Any | None,
    order_by: list[OrderByExpression] | None,
) -> list[Any]:
    """Build the window ORDER BY column list for adjacent video lookup."""
    order_col: list[Any] = []
    if ordering_expression is not None:
        if isinstance(ordering_expression, list):
            order_col.extend(ordering_expression)
        else:
            order_col.append(ordering_expression)
    if order_by:
        order_col.extend(expr.to_column_element() for expr in order_by)
        tiebreaker = (
            col(VideoTable.file_path_abs).asc()
            if order_by[0].ascending
            else col(VideoTable.file_path_abs).desc()
        )
        order_col.append(tiebreaker)
    elif not order_col:
        order_col.append(col(VideoTable.file_path_abs).asc())
    return order_col


def _base_query(
    ordering_expression: Any | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> Select[Any]:
    order_col = _window_order_columns(
        ordering_expression=ordering_expression,
        order_by=order_by,
    )

    # Build the base query that orders samples and annotates each row with its
    # previous/next sample_id and row number.
    query: Select[Any] = (
        select(
            col(VideoTable.sample_id).label("sample_id"),
            func.lag(col(VideoTable.sample_id))
            .over(order_by=order_col)
            .label("previous_sample_id"),
            func.lead(col(VideoTable.sample_id)).over(order_by=order_col).label("next_sample_id"),
            func.row_number().over(order_by=order_col).label("row_number"),
        )
        .select_from(VideoTable)
        .join(VideoTable.sample)
    )

    if order_by:
        for expr in order_by:
            query = expr.apply_joins(query)

    return query
