"""Get the MCAP sequences adjacent to a given sequence."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, func
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.resolvers import adjacents, mcap_group_sequence_resolver, similarity_utils
from lightly_studio.resolvers.mcap_group_sequence_resolver import sequence_grid_query
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)


def get_adjacent_sequences(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: McapSequenceFilter | None = None,
    text_embedding: list[float] | None = None,
) -> AdjacentResultView | None:
    """Get the MCAP sequences adjacent to a given sequence in its collection.

    The scope and the order are the same as in ``get_all_by_collection_id``: the filters
    and, with ``text_embedding``, only sequences with an embedding ordered by similarity.
    The order then continues by ascending ``created_at`` and ``sample_id``.

    Args:
        session: Database session.
        sample_id: The anchor sequence whose neighbours we want.
        collection_id: The SEQUENCE collection the anchor and neighbours belong to.
        filters: Optional filters of the sequences grid.
        text_embedding: Optional embedding to order the sequences by similarity to.

    Returns:
        The adjacency result with the previous/next sequence IDs and the anchor's
        position, or ``None`` when the anchor is not an MCAP sequence of the filtered
        collection.
    """
    mcap_group_sequence_resolver.resolve_embedding_region(
        session=session, collection_id=collection_id, sequence_filter=filters
    )
    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )
    order_by = sequence_grid_query.default_order()
    if distance_expr is not None:
        order_by = [distance_expr, *order_by]
    samples_query = sequence_grid_query.scope_query(
        query=_window_query(order_by=order_by),
        collection_id=collection_id,
        embedding_model_id=embedding_model_id,
        filters=filters,
    )
    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=samples_query,
    )


def _window_query(order_by: list[ColumnElement[Any]]) -> Select[Any]:
    """Return a per-sequence window query with the previous/next IDs and row number."""
    sequence_id = col(McapGroupSequenceTable.sample_id)
    return select(
        sequence_id.label("sample_id"),
        func.lag(sequence_id).over(order_by=order_by).label("previous_sample_id"),
        func.lead(sequence_id).over(order_by=order_by).label("next_sample_id"),
        func.row_number().over(order_by=order_by).label("row_number"),
    ).select_from(McapGroupSequenceTable)
