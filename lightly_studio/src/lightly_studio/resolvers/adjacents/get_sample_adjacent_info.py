"""Shared helpers for retrieving adjacency information for samples."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView


def get_sample_adjacent_info(
    session: Session,
    sample_id: UUID,
    samples_query: Select[Any],
) -> AdjacentResultView | None:
    """Return adjacency information for a sample within the provided query."""
    adjacents_subquery = samples_query.subquery("adjacent_samples")
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
        return None

    previous_sample_id, sample_id_row, next_sample_id, row_number = adjacency_row

    return AdjacentResultView(
        previous_sample_id=previous_sample_id,
        sample_id=sample_id_row,
        next_sample_id=next_sample_id,
        current_sample_position=int(row_number),
        total_count=total_count,
    )
