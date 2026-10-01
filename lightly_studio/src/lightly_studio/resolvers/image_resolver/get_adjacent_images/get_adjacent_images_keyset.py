"""Keyset (seek) implementation of image adjacency — the fast path.

The seek engine lives in ``resolvers.adjacents.keyset_seek``; only the sort keys and the
base query are image-specific.

Needs a total, deterministic order over non-nullable columns; see
``get_adjacent_images._is_keyset_sortable`` for the eligibility check and
``get_adjacent_images_window`` for the fallback.
"""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.adjacents import keyset_seek
from lightly_studio.resolvers.image_filter import ImageFilter


def get_adjacent_images_keyset(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    """Find the previous/next image and the anchor's position via keyset seeks.

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

    anchor = keyset_seek.fetch_anchor(
        session=session,
        query=_keyset_query(
            columns=[column for column, _ in sort_keys],
            collection_id=collection_id,
            filters=filters,
        ).where(col(ImageTable.sample_id) == sample_id),
    )
    if anchor is None:
        # The sample is not part of the (filtered) collection.
        return None

    return keyset_seek.get_adjacent_result(
        session=session,
        sample_id=sample_id,
        base_query=_keyset_query(
            columns=[col(ImageTable.sample_id)],
            collection_id=collection_id,
            filters=filters,
        ),
        sort_keys=sort_keys,
        anchor=anchor,
    )


def _keyset_sort_keys(order_by: list[OrderByExpression] | None) -> list[keyset_seek.SortKey]:
    """Build the ordered, fully deterministic list of keyset sort keys.

    Mirrors the window query's ordering: the requested sort columns, then a
    ``file_path_abs`` tiebreaker (following the primary direction) when not already
    present, then ``sample_id`` as a unique final tiebreaker so the ordering — and
    therefore prev/next and the position count — is total and stable.
    """
    keys: list[keyset_seek.SortKey] = []
    has_file_path = False
    if order_by:
        for expr in order_by:
            field_expr = cast(OrderByField, expr)
            keys.append((field_expr.field.get_sqlmodel_field(), expr.ascending))
            if field_expr.field is ImageSampleField.file_path_abs:
                has_file_path = True

    if not has_file_path:
        primary_ascending = (not order_by) or order_by[0].ascending
        keys.append((col(ImageTable.file_path_abs), primary_ascending))

    keys.append((col(ImageTable.sample_id), True))
    return keys


def _keyset_query(
    columns: list[keyset_seek.SortColumn],
    collection_id: UUID,
    filters: ImageFilter | None,
) -> Any:
    """Select the given columns from the collection's images, with filters applied.

    Type is loosened to Any because the callers select different row shapes: sample ids for
    the seeks and counts, the sort-key tuple for the anchor.
    """
    query = (
        select(*columns)
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(col(SampleTable.collection_id) == collection_id)
    )
    if filters:
        query = filters.apply(query)
    return query
