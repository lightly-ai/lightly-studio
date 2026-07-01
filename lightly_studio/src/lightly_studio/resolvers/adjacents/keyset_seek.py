"""Shared keyset (seek) helpers for adjacency resolvers.

Keyset pagination seeks directly to the neighbours of an anchor row using its
sort-key values, avoiding the full sort + window scan over the whole collection
(LIG-9925). All sort keys must be non-nullable and the key list must be totally
ordered (end with a unique tiebreaker such as ``sample_id``) so prev/next and the
position count are deterministic.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import sqlalchemy
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.adjacents import AdjacentResultView

# A keyset sort key paired with its sort direction (True == ascending).
SortKey = tuple[ColumnElement[Any], bool]


def get_adjacent_result(
    session: Session,
    sample_id: UUID,
    base_query: SelectOfScalar[UUID],
    anchor: tuple[Any, ...],
    sort_keys: list[SortKey],
) -> AdjacentResultView:
    """Assemble adjacency info for an anchor from a keyset base query.

    Args:
        session: The database session.
        sample_id: The anchor sample id.
        base_query: A query selecting the candidate ``sample_id``s (filters applied),
            joined so every column in ``sort_keys`` is available.
        anchor: The anchor's sort-key values, in the same order as ``sort_keys``.
        sort_keys: The ordered, non-nullable keyset sort keys.

    Returns:
        The previous/next neighbours, the anchor's 1-based position, and the total
        count over ``base_query``.
    """
    next_sample_id = _seek_neighbor(
        session=session, base_query=base_query, sort_keys=sort_keys, anchor=anchor, forward=True
    )
    previous_sample_id = _seek_neighbor(
        session=session, base_query=base_query, sort_keys=sort_keys, anchor=anchor, forward=False
    )

    total_count = session.exec(
        select(sqlalchemy.func.count()).select_from(base_query.subquery())
    ).one()

    # Position is 1-based: number of rows strictly before the anchor, plus the anchor.
    count_before = session.exec(
        select(sqlalchemy.func.count()).select_from(
            base_query.where(keyset_condition(sort_keys, anchor, after=False)).subquery()
        )
    ).one()

    return AdjacentResultView(
        previous_sample_id=previous_sample_id,
        sample_id=sample_id,
        next_sample_id=next_sample_id,
        current_sample_position=count_before + 1,
        total_count=total_count,
    )


def keyset_condition(
    sort_keys: list[SortKey],
    anchor: tuple[Any, ...],
    *,
    after: bool,
) -> ColumnElement[bool]:
    """Build the lexicographic keyset comparison for rows after/before the anchor.

    For sort keys ``k0, k1, ...`` with anchor values ``v0, v1, ...`` the rows after
    the anchor are::

        (k0 AFTER v0)
        OR (k0 == v0 AND k1 AFTER v1)
        OR ...

    where ``AFTER`` is ``>`` for an ascending key and ``<`` for a descending key
    (flipped when ``after`` is False). All keys are non-nullable, so no NULL
    handling is required.
    """
    or_terms: list[ColumnElement[bool]] = []
    for i, (column, ascending) in enumerate(sort_keys):
        equals_prefix = [sort_keys[j][0] == anchor[j] for j in range(i)]
        strictly_after = (column > anchor[i]) if ascending else (column < anchor[i])
        comparison = strictly_after if after else (~strictly_after) & (column != anchor[i])
        or_terms.append(sqlalchemy.and_(*equals_prefix, comparison))
    return sqlalchemy.or_(*or_terms)


def _seek_neighbor(
    session: Session,
    base_query: SelectOfScalar[UUID],
    sort_keys: list[SortKey],
    anchor: tuple[Any, ...],
    *,
    forward: bool,
) -> UUID | None:
    """Return the sample_id immediately after (forward) or before the anchor."""
    condition = keyset_condition(sort_keys, anchor, after=forward)
    order_columns = [
        _directional_column(column, ascending=ascending, forward=forward)
        for column, ascending in sort_keys
    ]
    query = base_query.where(condition).order_by(*order_columns).limit(1)
    return session.exec(query).first()


def _directional_column(
    column: ColumnElement[Any], *, ascending: bool, forward: bool
) -> ColumnElement[Any]:
    """Apply ASC/DESC for the seek direction (reversed when seeking backwards)."""
    effective_ascending = ascending if forward else not ascending
    return column.asc() if effective_ascending else column.desc()
