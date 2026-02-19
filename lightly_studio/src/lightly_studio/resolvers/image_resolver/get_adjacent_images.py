"""This module contains the resolver for getting adjacent images for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import adjacents, similarity_utils
from lightly_studio.resolvers.image_filter import ImageFilter


def get_adjacent_images(
    session: Session,
    sample_id: UUID,
    filters: ImageFilter,
    text_embedding: list[float] | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent images for a given sample ID."""
    collection_id = filters.sample_filter.collection_id if filters.sample_filter else None
    if collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")

    base_query = _base_query()

    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        base_query = similarity_utils.apply_similarity_join(
            query=_base_query(ordering_expression=[distance_expr]),
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


def _base_query(ordering_expression: Any | None = None) -> Select[Any]:
    ordering_expression = ordering_expression or col(ImageTable.file_path_abs).asc()

    # Build the base query that orders samples by absolute file path and
    # annotates each row with its previous/next sample_id and row number
    return (
        select(
            col(ImageTable.sample_id).label("sample_id"),
            func.lag(col(ImageTable.sample_id))
            .over(order_by=ordering_expression)
            .label("previous_sample_id"),
            func.lead(col(ImageTable.sample_id))
            .over(order_by=ordering_expression)
            .label("next_sample_id"),
            func.row_number().over(order_by=ordering_expression).label("row_number"),
        )
        .select_from(ImageTable)
        .join(ImageTable.sample)
    )
