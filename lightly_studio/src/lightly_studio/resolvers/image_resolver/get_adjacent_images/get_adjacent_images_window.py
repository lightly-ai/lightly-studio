"""Window-function implementation of adjacency lookup — the general fallback.

This path sorts the whole (filtered) collection and uses ``lag`` / ``lead`` /
``row_number`` window functions to read each row's neighbours and position in a
single pass. It is slower than the keyset path but handles cases the keyset seek
cannot express: similarity search and sorts over joined, nullable columns
(metadata, evaluation metrics). See ``get_adjacent_images._is_keyset_sortable``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import adjacents, similarity_utils
from lightly_studio.resolvers.image_filter import ImageFilter


def get_adjacent_images_window(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    distance_expr: ColumnElement[float] | None,
    embedding_model_id: UUID | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    """Find the previous/next image and the anchor's position via window functions.

    Builds a per-image window query ordered by (optionally) similarity distance and
    the requested sort, applies the similarity join and filters, then delegates the
    neighbour/position extraction to ``adjacents.get_sample_adjacent_info``.

    Args:
        session: Database session.
        sample_id: The anchor sample whose neighbours we want.
        collection_id: Collection the anchor and neighbours belong to.
        filters: Optional image filters constraining the collection.
        distance_expr: Similarity distance expression to sort by, or ``None``.
        embedding_model_id: Embedding model for the similarity join, or ``None``.
        order_by: Requested dataset sort; may be empty for the default sort.

    Returns:
        The adjacency result, or ``None`` if the anchor is filtered out.
    """
    # TODO(Horatiu, 06/2026): Unify ordering for adjacency queries. Similarity sort is
    # injected via ``ordering_expression`` and rebuilds the window query, while dataset
    # ``order_by`` uses ``OrderByExpression`` — see ``_base_query`` for assumptions.
    base_query = _base_query(order_by=order_by)
    base_query = base_query.where(col(SampleTable.collection_id) == collection_id)

    if distance_expr is not None and embedding_model_id is not None:
        base_query = similarity_utils.apply_similarity_join(
            query=_base_query(
                ordering_expression=[distance_expr],
            ).where(col(SampleTable.collection_id) == collection_id),
            sample_id_column=col(ImageTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    if filters:
        base_query = filters.apply(base_query)

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _base_query(
    ordering_expression: Any | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> Select[Any]:
    """Return a per-image window query for adjacency lookup.

    Rows are ordered by ``ordering_expression``, then ``order_by``, then an optional
    ``file_path_abs`` tiebreaker (default sort when both are omitted). Each row
    includes ``sample_id``, ``previous_sample_id``, ``next_sample_id``, and
    ``row_number`` via ``lag`` / ``lead`` / ``row_number`` over that ordering.

    Args:
        ordering_expression: Extra sort keys passed through to the window
            ``ORDER BY`` (e.g. similarity distance). Caller must add any JOINs
            these expressions need.
        order_by: Dataset sort expressions; JOINs are applied via ``apply_joins``.

    Returns:
        Query consumed by ``get_sample_adjacent_info``.
    """
    order_col = _window_order_columns(ordering_expression=ordering_expression, order_by=order_by)

    query: Select[Any] = (
        select(
            col(ImageTable.sample_id).label("sample_id"),
            sqlalchemy.func.lag(col(ImageTable.sample_id))
            .over(order_by=order_col)
            .label("previous_sample_id"),
            sqlalchemy.func.lead(col(ImageTable.sample_id))
            .over(order_by=order_col)
            .label("next_sample_id"),
            sqlalchemy.func.row_number().over(order_by=order_col).label("row_number"),
        )
        .select_from(ImageTable)
        .join(ImageTable.sample)
    )

    if order_by:
        for expr in order_by:
            query = expr.apply_joins(query)

    return query


def _window_order_columns(
    ordering_expression: Any | None,
    order_by: list[OrderByExpression] | None,
) -> Any:
    """Assemble the window ``ORDER BY`` from similarity, dataset sort, and tiebreaker.

    A ``file_path_abs`` tiebreaker (following the primary sort direction) is appended
    unless the dataset sort already sorts by ``file_path_abs``, keeping the ordering
    deterministic. With no explicit ordering at all, falls back to ``file_path_abs``.
    """
    needs_tiebreaker = not order_by or not any(
        isinstance(expr, OrderByField) and expr.field is ImageSampleField.file_path_abs
        for expr in order_by
    )
    if needs_tiebreaker:
        file_path_col = col(ImageTable.file_path_abs)
        tiebreaker_col = (
            file_path_col.asc() if (not order_by or order_by[0].ascending) else file_path_col.desc()
        )
        tiebreaker = [tiebreaker_col]
    else:
        tiebreaker = []

    if ordering_expression is not None:
        return (
            ordering_expression + [expr.to_column_element() for expr in order_by] + tiebreaker
            if order_by
            else [*ordering_expression, *tiebreaker]
        )
    if order_by:
        return [expr.to_column_element() for expr in order_by] + tiebreaker
    return col(ImageTable.file_path_abs).asc()
