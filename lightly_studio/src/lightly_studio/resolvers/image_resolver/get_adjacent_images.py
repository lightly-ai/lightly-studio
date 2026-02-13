"""This module contains the resolver for getting adjacent images for a given sample ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.adjacents import AdjancentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.similarity_utils import apply_similarity_join, get_distance_expression


def get_adjacent_images(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_id: UUID,
    text_embedding: list[float] | None = None,
    filters: ImageFilter | None = None,
    sample_ids: list[UUID] | None = None,
) -> AdjancentResultView:
    """Get the adjacent images for a given sample ID."""
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        return _get_all_with_similarity(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            sample_id=sample_id,
            filters=filters,
            sample_ids=sample_ids,
        )

    return _get_all_without_similarity(
        session=session,
        collection_id=collection_id,
        sample_id=sample_id,
        filters=filters,
        sample_ids=sample_ids,
    )


def _get_all_with_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    sample_id: UUID,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
) -> AdjancentResultView:
    """Get the adjacent images for a given sample ID, using similarity search."""
    ordering_expression = col(ImageTable.file_path_abs).asc()

    samples_query = select(
        col(ImageTable.sample_id).label("sample_id"),
        func.lag(col(ImageTable.sample_id))
        .over(order_by=ordering_expression)
        .label("sample_previous_id"),
        func.lead(col(ImageTable.sample_id))
        .over(order_by=ordering_expression)
        .label("sample_next_id"),
        func.row_number().over(order_by=ordering_expression).label("row_number"),
    ).select_from(ImageTable)

    samples_query = apply_similarity_join(
        query=samples_query,
        sample_id_column=col(ImageTable.sample_id),
        embedding_model_id=embedding_model_id,
    )
    samples_query = samples_query.join(ImageTable.sample).where(
        SampleTable.collection_id == collection_id
    )

    if filters:
        samples_query = filters.apply(samples_query)

    # TODO(Leonardo, 02/2026): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))

    adjacents_subquery = samples_query.subquery("adjacent_samples")

    adjacency_row = session.exec(
        select(
            adjacents_subquery.c.sample_previous_id,
            adjacents_subquery.c.sample_id,
            adjacents_subquery.c.sample_next_id,
            adjacents_subquery.c.row_number,
        ).where(adjacents_subquery.c.sample_id == sample_id)
    ).first()

    if adjacency_row is None:
        return AdjancentResultView(
            sample_previous_id=None,
            sample_id=sample_id,
            sample_next_id=None,
            position=None,
        )

    position = int(adjacency_row.row_number) - 1 if adjacency_row.row_number is not None else None
    return AdjancentResultView(
        sample_previous_id=adjacency_row.sample_previous_id,
        sample_id=adjacency_row.sample_id,
        sample_next_id=adjacency_row.sample_next_id,
        position=position,
    )


def _get_all_without_similarity(
    session: Session,
    collection_id: UUID,
    sample_id: UUID,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
) -> AdjancentResultView:
    ordering_expression = col(ImageTable.file_path_abs).asc()

    samples_query = select(
        col(ImageTable.sample_id).label("sample_id"),
        func.lag(col(ImageTable.sample_id))
        .over(order_by=ordering_expression)
        .label("sample_previous_id"),
        func.lead(col(ImageTable.sample_id))
        .over(order_by=ordering_expression)
        .label("sample_next_id"),
        func.row_number().over(order_by=ordering_expression).label("row_number"),
    ).select_from(ImageTable)
    samples_query = samples_query.join(ImageTable.sample).where(
        SampleTable.collection_id == collection_id
    )

    if filters:
        samples_query = filters.apply(samples_query)

    # TODO(Leonardo, 02/2026): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))

    adjacents_subquery = samples_query.subquery("adjacent_samples")

    adjacency_row = session.exec(
        select(
            adjacents_subquery.c.sample_previous_id,
            adjacents_subquery.c.sample_id,
            adjacents_subquery.c.sample_next_id,
            adjacents_subquery.c.row_number,
        ).where(adjacents_subquery.c.sample_id == sample_id)
    ).first()

    if adjacency_row is None:
        return AdjancentResultView(
            sample_previous_id=None,
            sample_id=sample_id,
            sample_next_id=None,
            position=None,
        )

    position = int(adjacency_row.row_number) - 1 if adjacency_row.row_number is not None else None
    return AdjancentResultView(
        sample_previous_id=adjacency_row.sample_previous_id,
        sample_id=adjacency_row.sample_id,
        sample_next_id=adjacency_row.sample_next_id,
        position=position,
    )
