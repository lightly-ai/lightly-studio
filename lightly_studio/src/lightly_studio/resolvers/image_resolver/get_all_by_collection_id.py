"""Implementation of get_all_by_collection_id function for images."""

from __future__ import annotations

from collections.abc import Sequence
from typing import cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByExpression,
    OrderByField,
    get_order_value,
)
from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)


def _file_path_abs_in_order_by(order_by: list[OrderByExpression]) -> bool:
    return any(
        isinstance(expr, OrderByField) and expr.field is ImageSampleField.file_path_abs
        for expr in order_by
    )


def _coerce_order_value(value: object) -> float | None:
    """Convert a raw SQL sort value to a float suitable for ``ImageView.order_value``.

    Only numeric values are converted; booleans return ``None``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


class GetAllSamplesByCollectionIdResult(BaseModel):
    """Result of getting all samples."""

    samples: Sequence[ImageTable]
    total_count: int
    next_cursor: int | None = None
    similarity_scores: Sequence[float] | None = None
    order_values: Sequence[float | None] | None = None


def _get_load_options() -> LoaderOption:
    """Get common load options for the sample relationship."""
    return selectinload(ImageTable.sample).options(
        selectinload(SampleTable.tags),
        # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
        joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
        selectinload(SampleTable.captions),
        selectinload(SampleTable.annotations).options(
            joinedload(AnnotationBaseTable.annotation_label),
            joinedload(AnnotationBaseTable.object_detection_details),
            joinedload(AnnotationBaseTable.segmentation_details),
            selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
        ),
    )


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute next cursor for pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    filters: ImageFilter | None = None,
    text_embedding: list[float] | None = None,
    sample_ids: list[UUID] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> GetAllSamplesByCollectionIdResult:
    """Retrieve samples for a specific collection with optional filtering."""
    # Resolve any embedding-plot region selection to concrete sample ids on the filter before the
    # query is built (the point-in-polygon test needs the session, which `apply` lacks).
    sample_filter = filters.sample_filter if filters is not None else None
    if sample_filter is not None and sample_filter.embedding_region is not None:
        sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
            session=session,
            collection_id=collection_id,
            region=sample_filter.embedding_region,
        )

    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        return _get_all_with_similarity(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            distance_expr=distance_expr,
            pagination=pagination,
            filters=filters,
            sample_ids=sample_ids,
        )
    return _get_all_without_similarity(
        session=session,
        collection_id=collection_id,
        pagination=pagination,
        filters=filters,
        sample_ids=sample_ids,
        order_by=order_by,
    )


def _get_all_with_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    distance_expr: ColumnElement[float],
    pagination: Paginated | None,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
) -> GetAllSamplesByCollectionIdResult:
    """Get samples with similarity search - returns (ImageTable, float) tuples."""
    load_options = _get_load_options()

    samples_query = (
        select(ImageTable, distance_expr)
        .options(load_options)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    samples_query = apply_similarity_join(
        query=samples_query,
        sample_id_column=col(ImageTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    total_count_query = apply_similarity_join(
        query=total_count_query,
        sample_id_column=col(ImageTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(
            db_array.in_array(column=col(ImageTable.sample_id), values=sample_ids)
        )
        total_count_query = total_count_query.where(
            db_array.in_array(column=col(ImageTable.sample_id), values=sample_ids)
        )

    samples_query = samples_query.order_by(distance_expr, col(ImageTable.file_path_abs).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    samples = [r[0] for r in results]
    similarity_scores = [distance_to_similarity(r[1]) for r in results]

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
        similarity_scores=similarity_scores,
        order_values=None,
    )


def _get_all_without_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    filters: ImageFilter | None,
    sample_ids: list[UUID] | None,
    order_by: list[OrderByExpression] | None,
) -> GetAllSamplesByCollectionIdResult:
    """Get samples without similarity search.

    When ``order_by`` is omitted, sorting defaults to ``file_path_abs`` ascending;
    otherwise a ``file_path_abs`` tiebreaker is appended when missing. The primary sort expression
    is appended to the SELECT so its value can be returned per row in ``order_values``.
    Non-numeric sort values (e.g. strings) are coerced to ``None``.
    """
    load_options = _get_load_options()

    samples_query: SelectOfScalar[ImageTable] = (
        select(ImageTable)
        .options(load_options)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(
            db_array.in_array(column=col(ImageTable.sample_id), values=sample_ids)
        )
        total_count_query = total_count_query.where(
            db_array.in_array(column=col(ImageTable.sample_id), values=sample_ids)
        )

    total_count = session.exec(total_count_query).one()
    next_cursor = _compute_next_cursor(pagination, total_count)

    # Add `file_path_abs` tiebreaker to `order_by`.
    if not order_by:
        order_by = [OrderByField(field=ImageSampleField.file_path_abs).asc()]
    else:
        # Copy so appending the tiebreaker does not mutate the caller's list.
        order_by = list(order_by)
        if not _file_path_abs_in_order_by(order_by):
            order_by.append(
                OrderByField(field=ImageSampleField.file_path_abs).asc()
                if order_by[0].ascending
                else OrderByField(field=ImageSampleField.file_path_abs).desc()
            )

    # Append the primary sort value to the SELECT so it can be returned per row.
    # Secondary expressions only contribute joins and ORDER BY.
    ordered_query = order_by[0].apply_with_order_value(samples_query)
    for expr in order_by[1:]:
        ordered_query = expr.apply_joins(ordered_query)
        ordered_query = ordered_query.order_by(expr.to_column_element())
    if pagination is not None:
        ordered_query = ordered_query.offset(pagination.offset).limit(pagination.limit)

    # Multi-column rows: ImageTable at index 0, sort value read by label.
    rows = session.execute(ordered_query).all()
    samples = [cast(ImageTable, row[0]) for row in rows]
    order_values = [_coerce_order_value(get_order_value(row)) for row in rows]

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=next_cursor,
        similarity_scores=None,
        order_values=order_values,
    )
