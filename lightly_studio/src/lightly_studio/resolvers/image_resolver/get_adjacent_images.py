"""This module contains the resolver for getting adjacent images for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.core.dataset_query.order_by import OrderByField
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
    order_by: list[OrderByField] | None = None,
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
            query=_base_query(ordering_expression=[distance_expr], order_by=order_by).where(
                col(SampleTable.collection_id) == collection_id
            ),
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
    order_by: list[OrderByField] | None = None,
) -> Select[Any]:
    tiebreaker = col(ImageTable.sample_id).asc()
    if ordering_expression is not None:
        order_col = (
            ordering_expression + [expr.to_column_element() for expr in order_by] + [tiebreaker]
            if order_by
            else [*ordering_expression, tiebreaker]
        )
    elif order_by:
        order_col = [expr.to_column_element() for expr in order_by] + [tiebreaker]
    else:
        order_col = col(ImageTable.file_path_abs).asc()

    # Build the base query that orders samples by absolute file path and
    # annotates each row with its previous/next sample_id and row number
    return (
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
