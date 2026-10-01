"""Keyset (seek) engine shared by the adjacency resolvers.

Reads the anchor row's sort-key values once, then jumps straight to its neighbours with
``LIMIT 1`` queries instead of sorting the whole collection and scanning it with window
functions. Position and total come from two ``COUNT``s. Callers supply the sort keys and
the base query, so resolvers for different sample types can share the engine.
"""

from __future__ import annotations

from typing import Any, Union
from uuid import UUID

import sqlalchemy
from sqlalchemy.orm import Mapped
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.adjacents import AdjacentResultView

# A sort key column, either built as an expression or taken from a model with ``col()``.
SortColumn = Union[ColumnElement[Any], Mapped[Any]]

# A keyset sort key paired with its sort direction (True == ascending).
SortKey = tuple[SortColumn, bool]


def get_adjacent_result(
    session: Session,
    sample_id: UUID,
    base_query: SelectOfScalar[UUID],
    sort_keys: list[SortKey],
    anchor: tuple[Any, ...],
) -> AdjacentResultView:
    """Assemble the adjacency result from two seeks and two counts.

    Args:
        session: Database session.
        sample_id: The anchor sample, already known to be in ``base_query``.
        base_query: Selects the candidate sample ids, filters applied.
        sort_keys: The total, deterministic ordering to seek along.
        anchor: The anchor's sort-key values, positionally aligned with ``sort_keys``.

    Returns:
        The neighbours plus the anchor's 1-based position and the total.
    """
    return AdjacentResultView(
        previous_sample_id=_seek_neighbor(
            session=session,
            base_query=base_query,
            sort_keys=sort_keys,
            anchor=anchor,
            forward=False,
        ),
        sample_id=sample_id,
        next_sample_id=_seek_neighbor(
            session=session,
            base_query=base_query,
            sort_keys=sort_keys,
            anchor=anchor,
            forward=True,
        ),
        # Position is 1-based: the rows strictly before the anchor, plus the anchor.
        current_sample_position=_count(
            session=session,
            query=base_query.where(
                _keyset_condition(sort_keys=sort_keys, anchor=anchor, after=False)
            ),
        )
        + 1,
        total_count=_count(session=session, query=base_query),
    )


def fetch_anchor(session: Session, query: SelectOfScalar[Any]) -> tuple[Any, ...] | None:
    """Read the anchor's sort-key values, or ``None`` if it is not in the filtered set.

    The returned tuple is aligned positionally with the query's select list and is the
    reference point every seek and count compares against.
    """
    row = session.exec(query).first()
    if row is None:
        return None
    return tuple(row)


def _seek_neighbor(
    session: Session,
    base_query: SelectOfScalar[UUID],
    sort_keys: list[SortKey],
    anchor: tuple[Any, ...],
    forward: bool,
) -> UUID | None:
    """Return the sample_id immediately after (forward) or before the anchor.

    Restricts ``base_query`` to rows on the requested side of the anchor, orders them so
    the closest neighbour comes first (the sort is reversed when seeking backwards), and
    takes the first row.
    """
    condition = _keyset_condition(sort_keys=sort_keys, anchor=anchor, after=forward)
    order_columns = [
        _directional_column(column=column, ascending=ascending, forward=forward)
        for column, ascending in sort_keys
    ]
    query = base_query.where(condition).order_by(*order_columns).limit(1)
    return session.exec(query).first()


def _directional_column(
    column: SortColumn, *, ascending: bool, forward: bool
) -> ColumnElement[Any]:
    """Apply ASC/DESC for the seek direction (reversed when seeking backwards)."""
    effective_ascending = ascending if forward else not ascending
    return column.asc() if effective_ascending else column.desc()


def _keyset_condition(
    sort_keys: list[SortKey],
    anchor: tuple[Any, ...],
    *,
    after: bool,
) -> ColumnElement[bool]:
    """Build the lexicographic comparison for the rows after (or before) the anchor.

    For keys ``k0, k1, ...`` and anchor values ``v0, v1, ...``::

        k0 > v0 OR (k0 = v0 AND k1 > v1) OR ...

    with ``>`` flipped to ``<`` for descending keys and for ``after=False``. All keys are
    non-nullable, so NULLs need no handling.

    The comparison is ANDed with ``k0 >= v0``, which is implied and changes no results.
    Planners only turn a *single-column* comparison into an index range condition; without
    it PostgreSQL applies the whole disjunction as a filter and scans the index from the
    start. Measured on 1M images with the anchor at position 800k, one seek went from 92ms
    (``Rows Removed by Filter: 800000``) to 0.03ms.
    """
    or_terms: list[ColumnElement[bool]] = []
    for i, (column, ascending) in enumerate(sort_keys):
        equals_prefix = [sort_keys[j][0] == anchor[j] for j in range(i)]
        # "After" means greater for an ascending key, smaller for a descending key;
        # seeking backwards (after=False) flips both.
        seek_greater = ascending if after else not ascending
        comparison = (column > anchor[i]) if seek_greater else (column < anchor[i])
        or_terms.append(sqlalchemy.and_(*equals_prefix, comparison))

    leading_column, leading_ascending = sort_keys[0]
    leading_seek_greater = leading_ascending if after else not leading_ascending
    leading_bound = (
        leading_column >= anchor[0] if leading_seek_greater else leading_column <= anchor[0]
    )
    return sqlalchemy.and_(sqlalchemy.or_(*or_terms), leading_bound)


def _count(session: Session, query: SelectOfScalar[UUID]) -> int:
    """Count the rows a sample-id query returns."""
    return session.exec(select(sqlalchemy.func.count()).select_from(query.subquery())).one()
