"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjancentResultView
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations(
    session: Session,
    annotation_id: UUID,
    filters: AnnotationsFilter,
) -> AdjancentResultView:
    """Get the adjacent annotations for a given annotation ID."""
    if not filters.collection_ids:
        raise ValueError("Collection IDs must be provided in filters.")

    base_query = _base_query()

    return _build_query(
        query=base_query,
        session=session,
        annotation_id=annotation_id,
        filters=filters,
    )


def _base_query(ordering_expression: Any | None = None) -> Select[Any]:
    ordering_expression = ordering_expression or [
        func.coalesce(ImageTable.file_path_abs, VideoTable.file_path_abs, "").asc(),
        col(AnnotationBaseTable.created_at).asc(),
        col(AnnotationBaseTable.sample_id).asc(),
    ]

    return (
        select(
            col(AnnotationBaseTable.sample_id).label("sample_id"),
            func.lag(col(AnnotationBaseTable.sample_id))
            .over(order_by=ordering_expression)
            .label("previous_sample_id"),
            func.lead(col(AnnotationBaseTable.sample_id))
            .over(order_by=ordering_expression)
            .label("next_sample_id"),
            func.row_number().over(order_by=ordering_expression).label("row_number"),
        )
        .select_from(AnnotationBaseTable)
        .outerjoin(
            ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id)
        )
        .outerjoin(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .outerjoin(VideoTable, col(VideoTable.sample_id) == col(VideoFrameTable.parent_sample_id))
    )


def _build_query(
    query: Any,
    session: Session,
    annotation_id: UUID,
    filters: AnnotationsFilter,
) -> AdjancentResultView:
    samples_query = query

    if filters:
        samples_query = filters.apply(samples_query)

    adjacents_subquery = samples_query.subquery("adjacent_annotations")
    total_count = session.exec(select(func.count()).select_from(adjacents_subquery)).one()

    adjacency_row = session.exec(
        select(
            adjacents_subquery.c.previous_sample_id,
            adjacents_subquery.c.sample_id,
            adjacents_subquery.c.next_sample_id,
            adjacents_subquery.c.row_number,
        ).where(adjacents_subquery.c.sample_id == annotation_id)
    ).first()
    if adjacency_row is None:
        return AdjancentResultView(
            previous_sample_id=None,
            sample_id=annotation_id,
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
