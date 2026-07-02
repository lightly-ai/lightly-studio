"""Keyset (seek) implementation of adjacency lookup — the fast path.

Instead of sorting the whole collection and scanning it with window functions, we
read the anchor sample's sort-key values once and then issue small ``LIMIT 1``
"seek" queries to jump straight to the neighbours. Position and total are answered
with two ``COUNT`` queries. None of these touch more than the rows they need, so
the cost is independent of the collection size.

This only works for sorts that produce a total, deterministic order over
non-nullable columns; see ``get_adjacent_images._is_keyset_sortable`` for the
eligibility check and ``get_adjacent_images_window`` for the fallback.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

import sqlalchemy
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter

# A keyset sort key paired with its sort direction (True == ascending).
_SortKey = tuple[ColumnElement[Any], bool]


def get_adjacent_images_keyset(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    """Find the previous/next image and the anchor's position via keyset seeks.

    Runs four cheap queries against the (filtered) collection:

    1. Fetch the anchor's sort-key values. Returns ``None`` if the anchor is not
       part of the filtered collection.
    2. Seek the first row strictly after the anchor (the next neighbour).
    3. Seek the first row strictly before the anchor (the previous neighbour).
    4. Count the total rows and the rows before the anchor to derive the 1-based
       position.

    Args:
        session: Database session.
        sample_id: The anchor sample whose neighbours we want.
        collection_id: Collection the anchor and neighbours belong to.
        filters: Optional image filters constraining the collection.
        order_by: Requested sort; ``None`` means the default ``file_path_abs`` sort.

    Returns:
        The adjacency result, or ``None`` if the anchor is filtered out.
    """
    sort_keys = _keyset_sort_keys(order_by)

    anchor = _fetch_anchor_values(
        session=session,
        sample_id=sample_id,
        collection_id=collection_id,
        filters=filters,
        sort_keys=sort_keys,
    )
    if anchor is None:
        # The sample is not part of the (filtered) collection.
        return None

    base_query = _keyset_sample_id_query(collection_id=collection_id, filters=filters)

    next_sample_id = _seek_neighbor(
        session=session,
        base_query=base_query,
        sort_keys=sort_keys,
        anchor=anchor,
        forward=True,
    )
    previous_sample_id = _seek_neighbor(
        session=session,
        base_query=base_query,
        sort_keys=sort_keys,
        anchor=anchor,
        forward=False,
    )

    total_count = session.exec(
        select(sqlalchemy.func.count()).select_from(base_query.subquery())
    ).one()

    # Position is 1-based: number of rows strictly before the anchor, plus the anchor.
    count_before = session.exec(
        select(sqlalchemy.func.count()).select_from(
            base_query.where(
                _keyset_condition(sort_keys=sort_keys, anchor=anchor, after=False)
            ).subquery()
        )
    ).one()

    return AdjacentResultView(
        previous_sample_id=previous_sample_id,
        sample_id=sample_id,
        next_sample_id=next_sample_id,
        current_sample_position=count_before + 1,
        total_count=total_count,
    )


def _keyset_sort_keys(order_by: list[OrderByExpression] | None) -> list[_SortKey]:
    """Build the ordered, fully deterministic list of keyset sort keys.

    Mirrors the window query's ordering: the requested sort columns, then a
    ``file_path_abs`` tiebreaker (following the primary direction) when not already
    present, then ``sample_id`` as a unique final tiebreaker so the ordering — and
    therefore prev/next and the position count — is total and stable.
    """
    keys: list[_SortKey] = []
    has_file_path = False
    if order_by:
        for expr in order_by:
            field_expr = cast(OrderByField, expr)
            column = cast(ColumnElement[Any], field_expr.field.get_sqlmodel_field())
            keys.append((column, expr.ascending))
            if field_expr.field is ImageSampleField.file_path_abs:
                has_file_path = True

    if not has_file_path:
        primary_ascending = (not order_by) or order_by[0].ascending
        keys.append((cast(ColumnElement[Any], col(ImageTable.file_path_abs)), primary_ascending))

    keys.append((cast(ColumnElement[Any], col(ImageTable.sample_id)), True))
    return keys


def _keyset_sample_id_query(
    collection_id: UUID,
    filters: ImageFilter | None,
) -> SelectOfScalar[UUID]:
    """Select image ``sample_id``s in the collection, with filters applied."""
    query: SelectOfScalar[UUID] = (
        select(col(ImageTable.sample_id))
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if filters:
        query = filters.apply(query)
    return query


def _fetch_anchor_values(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    sort_keys: list[_SortKey],
) -> tuple[Any, ...] | None:
    """Return the anchor sample's sort-key values, or ``None`` if it is filtered out.

    The returned tuple is aligned positionally with ``sort_keys`` and is the
    reference point every seek and count compares against.
    """
    query: SelectOfScalar[Any] = (
        select(*[column for column, _ in sort_keys])
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(col(SampleTable.collection_id) == collection_id)
        .where(col(ImageTable.sample_id) == sample_id)
    )
    if filters:
        query = filters.apply(query)

    row = session.exec(query).first()
    if row is None:
        return None
    return tuple(row)


def _seek_neighbor(
    session: Session,
    base_query: SelectOfScalar[UUID],
    sort_keys: list[_SortKey],
    anchor: tuple[Any, ...],
    forward: bool,
) -> UUID | None:
    """Return the sample_id immediately after (forward) or before the anchor.

    Restricts ``base_query`` to rows on the requested side of the anchor, orders
    them so the closest neighbour comes first (the sort is reversed when seeking
    backwards), and takes the first row.
    """
    condition = _keyset_condition(sort_keys=sort_keys, anchor=anchor, after=forward)
    order_columns = [
        _directional_column(column=column, ascending=ascending, forward=forward)
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


def _keyset_condition(
    sort_keys: list[_SortKey],
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
    (and flipped for each key when ``after`` is False). All keys are non-nullable,
    so no NULL handling is required.
    """
    or_terms: list[ColumnElement[bool]] = []
    for i, (column, ascending) in enumerate(sort_keys):
        equals_prefix = [sort_keys[j][0] == anchor[j] for j in range(i)]
        # "After" means greater for an ascending key, smaller for a descending key;
        # seeking backwards (after=False) flips both.
        seek_greater = ascending if after else not ascending
        comparison = (column > anchor[i]) if seek_greater else (column < anchor[i])
        or_terms.append(sqlalchemy.and_(*equals_prefix, comparison))
    return sqlalchemy.or_(*or_terms)
