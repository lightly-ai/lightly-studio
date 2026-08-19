"""Window-function implementation of annotation adjacency.

Sorts the whole filtered set and reads the neighbours off it with ``lag``/``lead``/
``row_number``, so the cost grows with the collection size.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlmodel
from sqlalchemy import func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select, SelectOfScalar

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
) -> AdjacentResultView | None:
    """Get the adjacent annotations by sorting and windowing the whole filtered set."""
    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=_build_window_query(filters),
    )


def _build_window_query(filters: AnnotationsFilter) -> Select[Any]:
    # Start from raw annotation rows so tag filters can join/distinct before windowing.
    base_rows: SelectOfScalar[AnnotationBaseTable] = select(AnnotationBaseTable)
    filtered_rows = filters.apply(base_rows).subquery()

    # TODO(Jonas, 07/2026): No leading order key here, so next/prev drifts from the grid
    # whenever the grid sorts by similarity. A leading key added there must be added here.
    ordering_expression = annotation_ordering.build_order_by(
        file_path_abs=annotation_ordering.coalesced_file_path_abs_expression(),
        created_at=filtered_rows.c.created_at,
        annotation_sample_id=filtered_rows.c.sample_id,
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
