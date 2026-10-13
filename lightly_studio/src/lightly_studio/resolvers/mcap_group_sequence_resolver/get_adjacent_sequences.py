"""Get the MCAP sequences adjacent to a given sequence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import adjacents


def get_adjacent_sequences(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
) -> AdjacentResultView | None:
    """Get the MCAP sequences adjacent to a given sequence in its collection.

    The order is the same as in ``get_all_by_collection_id``: ascending ``created_at`` of
    the sequence sample, then ascending ``sample_id``.

    Args:
        session: Database session.
        sample_id: The anchor sequence whose neighbours we want.
        collection_id: The SEQUENCE collection the anchor and neighbours belong to.

    Returns:
        The adjacency result with the previous/next sequence IDs and the anchor's
        position, or ``None`` when the anchor is not an MCAP sequence of the collection.
    """
    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=_window_query(collection_id=collection_id),
    )


def _window_query(collection_id: UUID) -> Select[Any]:
    """Return a per-sequence window query with the previous/next IDs and row number."""
    order_by: list[ColumnElement[Any]] = [
        col(SampleTable.created_at).asc(),
        col(SampleTable.sample_id).asc(),
    ]
    sequence_id = col(McapGroupSequenceTable.sample_id)
    return (
        select(
            sequence_id.label("sample_id"),
            func.lag(sequence_id).over(order_by=order_by).label("previous_sample_id"),
            func.lead(sequence_id).over(order_by=order_by).label("next_sample_id"),
            func.row_number().over(order_by=order_by).label("row_number"),
        )
        .select_from(McapGroupSequenceTable)
        .join(SampleTable, sequence_id == col(SampleTable.sample_id))
        .where(col(SampleTable.collection_id) == collection_id)
    )
