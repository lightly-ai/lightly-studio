"""Resolver for getting adjacent annotations for a given annotation ID."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlmodel
from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select, SelectOfScalar

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

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=_build_window_query(filters),
    )


def _build_window_query(filters: AnnotationsFilter) -> Select[Any]:
    # Start from raw annotation rows so tag filters can join/distinct before windowing.
    base_rows: SelectOfScalar[AnnotationBaseTable] = select(AnnotationBaseTable)
    filtered_rows = filters.apply(base_rows).subquery()

    file_path_abs = func.coalesce(
        col(ImageTable.file_path_abs),
        col(VideoTable.file_path_abs),
        "",
    )
    ordering_expression: tuple[ColumnElement[Any], ColumnElement[Any], ColumnElement[Any]] = (
        file_path_abs.asc(),
        filtered_rows.c.created_at.asc(),
        filtered_rows.c.sample_id.asc(),
    )

    # Compute lag/lead/row_number on the already filtered set to avoid tag duplicates.
    return (
        select(
            filtered_rows.c.sample_id.label("sample_id"),
            func.lag(filtered_rows.c.sample_id)
            .over(order_by=ordering_expression)
            .label("previous_sample_id"),
            func.lead(filtered_rows.c.sample_id)
            .over(order_by=ordering_expression)
            .label("next_sample_id"),
            func.row_number().over(order_by=ordering_expression).label("row_number"),
        )
        .select_from(filtered_rows)
        .outerjoin(ImageTable, col(ImageTable.sample_id) == filtered_rows.c.parent_sample_id)
        .outerjoin(
            VideoFrameTable,
            col(VideoFrameTable.sample_id) == filtered_rows.c.parent_sample_id,
        )
        .outerjoin(
            VideoTable,
            col(VideoTable.sample_id) == sqlmodel.col(VideoFrameTable.parent_sample_id),
        )
    )
