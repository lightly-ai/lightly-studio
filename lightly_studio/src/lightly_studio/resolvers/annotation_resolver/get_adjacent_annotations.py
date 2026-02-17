"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import adjacents
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
) -> AdjacentResultView | None:
    """Get the adjacent annotations for a given annotation ID."""
    if not filters.collection_ids:
        raise ValueError("Collection IDs must be provided in filters.")

    base_query = _base_query()

    if filters:
        base_query = filters.apply(base_query)

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _base_query() -> Select[Any]:
    ordering_expression: tuple[ColumnElement[Any], ColumnElement[Any], ColumnElement[Any]] = (
        func.coalesce(ImageTable.file_path_abs, VideoTable.file_path_abs, "").asc(),
        col(AnnotationBaseTable.created_at).asc(),
        col(AnnotationBaseTable.sample_id).asc(),
    )

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
