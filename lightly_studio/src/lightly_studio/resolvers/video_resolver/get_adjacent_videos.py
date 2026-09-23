"""Resolver for getting adjacent videos for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
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
    """Get the adjacent videos for a given sample ID.

    Args:
        session: Database session.
        sample_id: The anchor sample whose neighbours we want.
        collection_id: Collection the anchor and neighbours belong to.
        filters: Optional video filters constraining the collection.
        text_embedding: Optional similarity query; when present it drives the
            ordering and ``order_by`` is ignored.
        order_by: Requested grid sort so prev/next follows it; empty for the
            default ``file_path_abs`` order.

    Returns:
        The adjacency result with the previous/next sample IDs and the anchor's
        position, or ``None`` when the anchor is not in the (filtered) collection.
    """
    base_query = _base_query(order_by=order_by)
    base_query = base_query.where(col(SampleTable.collection_id) == collection_id)

    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
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


# TODO(Horatiu, 06/2026): This window/tiebreaker builder duplicates
# get_adjacent_images_window; fold both into the shared adjacency-ordering unification
# tracked there rather than maintaining two copies.
def _base_query(
    ordering_expression: Any | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> Select[Any]:
    """Return a per-video window query for adjacency lookup.

    Rows are ordered by ``ordering_expression`` (similarity), then the requested
    ``order_by``, then a ``file_path_abs`` tiebreaker. Each row is annotated with its
    previous/next ``sample_id`` and row number via ``lag`` / ``lead`` / ``row_number``.

    Args:
        ordering_expression: Extra sort keys for the window ``ORDER BY`` (e.g. the
            similarity distance). The caller must add any JOINs these need.
        order_by: Grid sort expressions; their JOINs are applied via ``apply_joins``.
    """
    order_col = _window_order_columns(ordering_expression=ordering_expression, order_by=order_by)

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


def _window_order_columns(
    ordering_expression: Any | None,
    order_by: list[OrderByExpression] | None,
) -> Any:
    """Assemble the window ``ORDER BY`` from similarity, grid sort, and tiebreaker.

    A ``file_path_abs`` tiebreaker (following the primary sort direction) is appended
    unless the grid sort already sorts by ``file_path_abs``. With no explicit ordering,
    falls back to ``file_path_abs`` ascending. Mirrors the video grid resolver's
    tiebreaker rather than sharing a builder with the image window.
    """
    needs_tiebreaker = not order_by or not any(
        isinstance(expr, OrderByField) and expr.field is VideoSampleField.file_path_abs
        for expr in order_by
    )
    if needs_tiebreaker:
        file_path_col = col(VideoTable.file_path_abs)
        tiebreaker_col = (
            file_path_col.asc() if (not order_by or order_by[0].ascending) else file_path_col.desc()
        )
        tiebreaker = [tiebreaker_col]
    else:
        tiebreaker = []

    # Similarity and grid sort never arrive together: the similarity call passes only
    # ``ordering_expression``, the grid call passes only ``order_by``.
    if ordering_expression is not None:
        return [*ordering_expression, *tiebreaker]
    if order_by:
        return [e for expr in order_by for e in expr.to_column_elements()] + tiebreaker
    return col(VideoTable.file_path_abs).asc()
