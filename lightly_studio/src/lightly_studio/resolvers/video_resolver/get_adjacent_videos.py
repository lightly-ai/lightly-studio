"""Resolver for getting adjacent videos for a given sample ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjancentResultView
from lightly_studio.models.video import VideoTable
from lightly_studio.resolvers import similarity_utils
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def get_adjacent_videos(
    session: Session,
    sample_id: UUID,
    filters: VideoFilter,
    text_embedding: list[float] | None = None,
) -> AdjancentResultView:
    """Get the adjacent videos for a given sample ID."""
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
            sample_id_column=col(VideoTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    return _build_query(
        query=base_query,
        session=session,
        sample_id=sample_id,
        filters=filters,
    )


def _base_query(ordering_expression: Any | None = None) -> Select[Any]:
    ordering_expression = ordering_expression or col(VideoTable.file_path_abs).asc()

    # Build the base query that orders samples by absolute file path and
    # annotates each row with its previous/next sample_id and row number
    return select(
        col(VideoTable.sample_id).label("sample_id"),
        func.lag(col(VideoTable.sample_id))
        .over(order_by=ordering_expression)
        .label("previous_sample_id"),
        func.lead(col(VideoTable.sample_id))
        .over(order_by=ordering_expression)
        .label("next_sample_id"),
        func.row_number().over(order_by=ordering_expression).label("row_number"),
    ).select_from(VideoTable)


def _build_query(
    query: Any,
    session: Session,
    sample_id: UUID,
    filters: VideoFilter,
) -> AdjancentResultView:
    samples_query = query.join(VideoTable.sample)

    if filters:
        samples_query = filters.apply(samples_query)

    # Create a subquery with adjacency information for all samples
    adjacents_subquery = samples_query.subquery("adjacent_videos")
    total_count = session.exec(select(func.count()).select_from(adjacents_subquery)).one()

    # Query the subquery to retrieve the previous/next sample IDs
    # and row number for the given sample_id
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
