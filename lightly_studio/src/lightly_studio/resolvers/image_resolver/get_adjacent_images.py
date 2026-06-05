"""This module contains the resolver for getting adjacent images for a given sample ID."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField, SelectQuery
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import adjacents, similarity_utils
from lightly_studio.resolvers.image_filter import ImageFilter


def get_adjacent_images(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent images for a given sample ID."""
    base_query = _base_query(order_by=order_by)
    base_query = base_query.where(col(SampleTable.collection_id) == collection_id)

    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

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
        order_col = (
            ordering_expression + [expr.to_column_element() for expr in order_by] + tiebreaker
            if order_by
            else [*ordering_expression, *tiebreaker]
        )
    elif order_by:
        order_col = [expr.to_column_element() for expr in order_by] + tiebreaker
    else:
        order_col = col(ImageTable.file_path_abs).asc()

    # Build the base query that orders samples by absolute file path and
    # annotates each row with its previous/next sample_id and row number
    query: Select[Any] = (
        select(
            col(ImageTable.sample_id).label("sample_id"),
            func.lag(col(ImageTable.sample_id))
            .over(order_by=order_col)
            .label("previous_sample_id"),
            func.lead(col(ImageTable.sample_id)).over(order_by=order_col).label("next_sample_id"),
            func.row_number().over(order_by=order_col).label("row_number"),
        )
        .select_from(ImageTable)
        .join(ImageTable.sample)
    )

    if order_by:
        for expr in order_by:
            query = cast(Select[Any], expr.apply(cast(SelectQuery, query), order=False))

    return query
