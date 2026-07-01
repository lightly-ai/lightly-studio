"""Keyset (seek) implementation of adjacency lookup — the fast path.

Instead of sorting the whole collection and scanning it with window functions, we
read the anchor sample's sort-key values once and then delegate to the shared
``resolvers.adjacents.keyset_seek`` helper, which issues small ``LIMIT 1`` "seek"
queries to jump straight to the neighbours and two ``COUNT`` queries for the
position/total. None of these touch more than the rows they need, so the cost is
independent of the collection size.

This only works for sorts that produce a total, deterministic order over
non-nullable columns; see ``_dispatch._is_keyset_sortable`` for the eligibility
check and ``_window`` for the fallback.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.adjacents import keyset_seek
from lightly_studio.resolvers.image_filter import ImageFilter

# A keyset sort key paired with its sort direction (True == ascending).
_SortKey = keyset_seek.SortKey


def get_adjacent_images_keyset(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    """Find the previous/next image and the anchor's position via keyset seeks.

    Fetches the anchor's sort-key values (returns ``None`` if the anchor is not
    part of the filtered collection), then delegates the seek/position/total
    lookups to ``keyset_seek.get_adjacent_result``.

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

    return keyset_seek.get_adjacent_result(
        session=session,
        sample_id=sample_id,
        base_query=base_query,
        anchor=anchor,
        sort_keys=sort_keys,
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
