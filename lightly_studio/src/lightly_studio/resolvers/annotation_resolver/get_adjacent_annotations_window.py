"""Window-function implementation of annotation adjacency.

Sorts the whole filtered set and reads the neighbours off it with ``lag``/``lead``/
``row_number``, so the cost grows with the collection size.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlmodel
from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from lightly_studio.core.dataset_query.order_by import OrderByAnnotationEvaluationMetricField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers import adjacents
from lightly_studio.resolvers.annotations import annotation_ordering
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter


def get_adjacent_annotations_window(
    session: Session,
    sample_id: UUID,
    filters: AnnotationsFilter,
    order_by: OrderByAnnotationEvaluationMetricField | None = None,
) -> AdjacentResultView | None:
    """Get the adjacent annotations by sorting and windowing the whole filtered set.

    Args:
        session: Database session.
        sample_id: The anchor annotation whose neighbours we want.
        filters: Annotation filters constraining the set; must scope the collection.
        order_by: Optional leading sort key applied before the tiebreaker chain.
    """
    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=_build_window_query(filters, order_by=order_by),
    )


def _build_window_query(
    filters: AnnotationsFilter,
    order_by: OrderByAnnotationEvaluationMetricField | None = None,
) -> Select[Any]:
    # Start from raw annotation rows so tag filters can join/distinct before windowing.
    base_rows: SelectOfScalar[AnnotationBaseTable] = select(AnnotationBaseTable)
    filtered_rows = filters.apply(base_rows).subquery()

    # The metric join must match against filtered_rows.c.sample_id, not the ORM table column,
    # because AnnotationBaseTable is not directly in the FROM — only the subquery is.
    if order_by is not None:
        order_by.annotation_id_column = filtered_rows.c.sample_id
        leading_order_key: ColumnElement[Any] | None = order_by.to_column_elements()[0]
    else:
        leading_order_key = None

    ordering_expression = annotation_ordering.build_order_by(
        file_path_abs=annotation_ordering.coalesced_file_path_abs_expression(),
        created_at=filtered_rows.c.created_at,
        annotation_sample_id=filtered_rows.c.sample_id,
        leading_order_key=leading_order_key,
    )

    # Compute lag/lead/row_number on the already filtered set to avoid tag duplicates.
    query: Select[Any] = (
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

    if order_by is not None:
        query = order_by.apply_joins(query)

    return query
