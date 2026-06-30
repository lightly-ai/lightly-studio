"""This module contains the resolver for getting adjacent images for a given sample ID."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, func, or_
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import adjacents, similarity_utils
from lightly_studio.resolvers.image_filter import ImageFilter

# A keyset sort key paired with its sort direction (True == ascending).
_SortKey = tuple[ColumnElement[Any], bool]


def get_adjacent_images(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> AdjacentResultView | None:
    """Get the previous and next image for a sample in the current sort order.

    Uses a keyset (seek) lookup for the common case — the default ``file_path_abs``
    sort or any sort over plain image columns — so prev/next and the position/total
    counts avoid the full sort + window scan over the whole collection (LIG-9925).
    Similarity search and joined/nullable sorts (metadata, evaluation metrics) fall
    back to the window-function implementation.
    """
    embedding_model_id, distance_expr = similarity_utils.get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is None and embedding_model_id is None and _is_keyset_sortable(order_by):
        return _get_adjacent_images_keyset(
            session=session,
            sample_id=sample_id,
            collection_id=collection_id,
            filters=filters,
            order_by=order_by,
        )

    return _get_adjacent_images_window(
        session=session,
        sample_id=sample_id,
        collection_id=collection_id,
        filters=filters,
        distance_expr=distance_expr,
        embedding_model_id=embedding_model_id,
        order_by=order_by,
    )


def _is_keyset_sortable(order_by: list[OrderByExpression] | None) -> bool:
    """Return whether the sort can be served by keyset seek.

    Keyset comparison needs non-nullable, single-column sort keys. Plain image
    columns (``OrderByField``) qualify; metadata / evaluation-metric sorts use
    outer joins and nullable values, so they keep the window implementation.
    """
    if not order_by:
        return True
    return all(isinstance(expr, OrderByField) for expr in order_by)


# --------------------------------------------------------------------------------------
# Keyset (seek) implementation — the fast path.
# --------------------------------------------------------------------------------------


def _get_adjacent_images_keyset(
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
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

    total_count = session.exec(select(func.count()).select_from(base_query.subquery())).one()

    # Position is 1-based: number of rows strictly before the anchor, plus the anchor.
    count_before = session.exec(
        select(func.count()).select_from(
            base_query.where(_keyset_condition(sort_keys, anchor, after=False)).subquery()
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
    """Return the current sample's sort-key values, or ``None`` if it is filtered out."""
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
    *,
    forward: bool,
) -> UUID | None:
    """Return the sample_id immediately after (forward) or before the anchor."""
    condition = _keyset_condition(sort_keys, anchor, after=forward)
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
    (flipped when ``after`` is False). All keys are non-nullable, so no NULL
    handling is required.
    """
    or_terms: list[ColumnElement[bool]] = []
    for i, (column, ascending) in enumerate(sort_keys):
        equals_prefix = [sort_keys[j][0] == anchor[j] for j in range(i)]
        strictly_after = (column > anchor[i]) if ascending else (column < anchor[i])
        comparison = strictly_after if after else (~strictly_after) & (column != anchor[i])
        or_terms.append(and_(*equals_prefix, comparison))
    return or_(*or_terms)


# --------------------------------------------------------------------------------------
# Window-function implementation — fallback for similarity search and complex sorts.
# --------------------------------------------------------------------------------------


def _get_adjacent_images_window(  # noqa: PLR0913
    session: Session,
    sample_id: UUID,
    collection_id: UUID,
    filters: ImageFilter | None,
    distance_expr: ColumnElement[float] | None,
    embedding_model_id: UUID | None,
    order_by: list[OrderByExpression] | None,
) -> AdjacentResultView | None:
    # TODO(Horatiu, 06/2026): Unify ordering for adjacency queries. Similarity sort is
    # injected via ``ordering_expression`` and rebuilds the window query, while dataset
    # ``order_by`` uses ``OrderByExpression`` — see ``_base_query`` for assumptions.
    base_query = _base_query(order_by=order_by)
    base_query = base_query.where(col(SampleTable.collection_id) == collection_id)

    if distance_expr is not None and embedding_model_id is not None:
        base_query = similarity_utils.apply_similarity_join(
            query=_base_query(
                ordering_expression=[distance_expr],
            ).where(col(SampleTable.collection_id) == collection_id),
            sample_id_column=col(ImageTable.sample_id),
            embedding_model_id=embedding_model_id,
        )

    if filters:
        base_query = filters.apply(base_query)

    return adjacents.get_sample_adjacent_info(
        session=session,
        sample_id=sample_id,
        samples_query=base_query,
    )


def _base_query(
    ordering_expression: Any | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> Select[Any]:
    """Return a per-image window query for adjacency lookup.

    Rows are ordered by ``ordering_expression``, then ``order_by``, then an optional
    ``file_path_abs`` tiebreaker (default sort when both are omitted). Each row
    includes ``sample_id``, ``previous_sample_id``, ``next_sample_id``, and
    ``row_number`` via ``lag`` / ``lead`` / ``row_number`` over that ordering.

    Args:
        ordering_expression: Extra sort keys passed through to the window
            ``ORDER BY`` (e.g. similarity distance). Caller must add any JOINs
            these expressions need.
        order_by: Dataset sort expressions; JOINs are applied via ``apply_joins``.

    Returns:
        Query consumed by ``get_sample_adjacent_info``.
    """
    needs_tiebreaker = not order_by or not any(
        isinstance(expr, OrderByField) and expr.field is ImageSampleField.file_path_abs
        for expr in order_by
    )
    if needs_tiebreaker:
        file_path_col = col(ImageTable.file_path_abs)
        tiebreaker_col = (
            file_path_col.asc() if (not order_by or order_by[0].ascending) else file_path_col.desc()
        )
        tiebreaker = [tiebreaker_col]
    else:
        tiebreaker = []
    if ordering_expression is not None:
        order_col = (
            ordering_expression + [expr.to_column_element() for expr in order_by] + tiebreaker
            if order_by
            else [*ordering_expression, *tiebreaker]
        )
    elif order_by:
        order_col = [expr.to_column_element() for expr in order_by] + tiebreaker
    else:
        order_col = col(ImageTable.file_path_abs).asc()

    query: Select[Any] = (
        select(
            col(ImageTable.sample_id).label("sample_id"),
            func.lag(col(ImageTable.sample_id))
            .over(order_by=order_col)
            .label("previous_sample_id"),
            func.lead(col(ImageTable.sample_id)).over(order_by=order_col).label("next_sample_id"),
            func.row_number().over(order_by=order_col).label("row_number"),
        )
        .select_from(ImageTable)
        .join(ImageTable.sample)
    )

    if order_by:
        for expr in order_by:
            query = expr.apply_joins(query)

    return query
