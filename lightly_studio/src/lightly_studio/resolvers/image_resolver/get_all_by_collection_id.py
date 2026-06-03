"""Implementation of get_all_by_collection_id function for images."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Union, cast
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import ColumnElement
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select
from sqlmodel.sql.expression import Select, SelectOfScalar
from typing_extensions import TypeAlias

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)

ImageSamplesQuery: TypeAlias = Union[Select[tuple[ImageTable, Any]], SelectOfScalar[ImageTable]]


def _file_path_abs_in_order_by(order_by: list[OrderByExpression]) -> bool:
    """Return True if ``file_path_abs`` is already used as a sort key."""
    return any(
        isinstance(expr, OrderByField) and expr.field is ImageSampleField.file_path_abs
        for expr in order_by
    )


def _has_metadata_join(filters: ImageFilter | None) -> bool:
    """Return True if filters already join SampleMetadataTable."""
    return (
        filters is not None
        and filters.sample_filter is not None
        and bool(filters.sample_filter.metadata_filters)
    )


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


def _coerce_order_value(value: object) -> float | None:
    """Convert a raw SQL sort value to a float suitable for ``ImageView.order_value``.

    Only numeric values are converted; booleans return ``None``.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _primary_order_value_column(
    primary_order_by: OrderByExpression | None,
) -> ColumnElement[Any] | None:
    """Return the SQL expression for the primary sort value, if selectable."""
    if primary_order_by is None:
        return None
    return primary_order_by.order_value_column()


def _apply_file_path_tiebreaker(
    samples_query: ImageSamplesQuery,
    ascending: bool,
) -> ImageSamplesQuery:
    """Append a ``file_path_abs`` ORDER BY tiebreaker in the given direction."""
    file_path_col = col(ImageTable.file_path_abs)
    tiebreaker = file_path_col.asc() if ascending else file_path_col.desc()
    return samples_query.order_by(tiebreaker)


def _apply_order_by_clauses(
    samples_query: ImageSamplesQuery,
    order_by: list[OrderByExpression],
    filters: ImageFilter | None,
) -> ImageSamplesQuery:
    """Apply joins and ORDER BY clauses for all sort expressions.

    Metadata and evaluation-metric joins are added at most once. When filters already
    join ``SampleMetadataTable``, a second metadata join is skipped. A ``file_path_abs``
    tiebreaker is appended unless it is already present in ``order_by``.
    """
    evaluation_metric_joined = False
    metadata_joined = _has_metadata_join(filters)

    for expr in order_by:
        if isinstance(expr, OrderByEvaluationMetricField):
            if not evaluation_metric_joined:
                samples_query = expr.apply_order_value_joins(samples_query)  # type: ignore[arg-type]
                evaluation_metric_joined = True
            samples_query = samples_query.order_by(expr.to_column_element())
        elif isinstance(expr, OrderByMetadataField):
            if not metadata_joined:
                samples_query = expr.apply_order_value_joins(samples_query)  # type: ignore[arg-type]
                metadata_joined = True
            samples_query = samples_query.order_by(expr.to_column_element())
        else:
            samples_query = expr.apply(samples_query)  # type: ignore[arg-type]

    if not _file_path_abs_in_order_by(order_by):
        samples_query = _apply_file_path_tiebreaker(samples_query, ascending=order_by[0].ascending)

    return samples_query


def _extract_order_values(
    results: Sequence[tuple[Any, ...]],
    order_value_index: int | None,
) -> list[float | None] | None:
    """Read coerced sort values from multi-column query rows at ``order_value_index``."""
    if order_value_index is None:
        return None
    return [_coerce_order_value(row[order_value_index]) for row in results]


def _split_query_results(
    results: Sequence[object],
    order_value_index: int | None,
) -> tuple[list[ImageTable], list[float | None] | None]:
    """Split SQLAlchemy results into images and optional parallel sort values.

    Single-column queries return bare ``ImageTable`` rows; multi-column queries return
    SQLAlchemy ``Row`` objects with the image at index 0 and the sort value at
    ``order_value_index``.
    """
    if not results:
        return [], None
    if order_value_index is None:
        return cast(list[ImageTable], list(results)), None
    samples = [row[0] for row in results]  # type: ignore[index]
    return samples, _extract_order_values(results, order_value_index)  # type: ignore[arg-type]


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
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

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

    When ``order_by`` is set, the primary sort expression is included in the SELECT
    so ``order_values`` can be returned alongside each ``ImageTable``. Without a sort,
    results default to ``file_path_abs`` ascending and ``order_values`` is ``None``.
    """
    load_options = _get_load_options()
    primary_order_by = order_by[0] if order_by else None
    order_value_col = _primary_order_value_column(primary_order_by)
    order_value_index = 1 if order_value_col is not None else None

    samples_query: ImageSamplesQuery
    if order_value_col is not None:
        samples_query = select(ImageTable, order_value_col).options(load_options)
    else:
        samples_query = select(ImageTable).options(load_options)
    samples_query = samples_query.join(ImageTable.sample).where(
        SampleTable.collection_id == collection_id
    )

    total_count_query = (
        select(func.count())
        .select_from(ImageTable)
        .join(ImageTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    if filters:
        if order_value_col is not None:
            samples_query = filters.apply(cast(Select[tuple[ImageTable, Any]], samples_query))
        else:
            samples_query = filters.apply(cast(SelectOfScalar[ImageTable], samples_query))
        total_count_query = filters.apply(total_count_query)

    # TODO(Michal, 06/2025): Consider adding sample_ids to the filters.
    if sample_ids:
        samples_query = samples_query.where(col(ImageTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(ImageTable.sample_id).in_(sample_ids))

    if order_by:
        samples_query = _apply_order_by_clauses(samples_query, order_by, filters)
    else:
        samples_query = samples_query.order_by(col(ImageTable.file_path_abs).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()
    samples, order_values = _split_query_results(results, order_value_index)

    return GetAllSamplesByCollectionIdResult(
        samples=samples,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
        similarity_scores=None,
        order_values=order_values,
    )
