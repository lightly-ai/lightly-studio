"""Run a dataset query through the active transport."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from uuid import UUID

from lightly_studio.core.dataset_query import query_expr_conversion
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.core.dataset_query.query_expr_conversion import UnsupportedQueryError
from lightly_studio.core.image.record_image_sample import RecordImageSample
from lightly_studio.models.collection import SampleType
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.sample_query import (
    DEFAULT_PAGE_SIZE,
    EvaluationMetricSortKey,
    SampleInclude,
    SampleQueryRequest,
    SortKey,
)
from lightly_studio.transport import active_transport


def build_request(
    sample_type: SampleType,
    match_expression: MatchExpression | None,
    order_by: Sequence[OrderByExpression],
    filters_sample_ids: bool,
    offset: int,
) -> SampleQueryRequest | None:
    """Build the request of a dataset query. None means the query uses SQL.

    Raises:
        UnsupportedQueryError: If the transport is remote and cannot send the query.
    """
    if not active_transport.use_transport_queries():
        return None
    try:
        query_expr = _to_image_query_expr(
            sample_type=sample_type,
            match_expression=match_expression,
            filters_sample_ids=filters_sample_ids,
        )
        sort = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=sample_type)
        needs_offset_paging = not all(
            _is_field_sort(key=key, table=sample_type.value) for key in sort
        )
        # Offset paging can skip samples that a loop changes, so local mode uses SQL.
        if needs_offset_paging and not active_transport.is_remote():
            return None
    except UnsupportedQueryError:
        if active_transport.is_remote():
            raise
        return None
    return SampleQueryRequest(
        query_expr=query_expr, sort=sort, offset=offset, include=[SampleInclude.TAGS]
    )


def build_export_request(
    sample_type: SampleType,
    match_expression: MatchExpression | None,
    order_by: Sequence[OrderByExpression],
    filters_sample_ids: bool,
    offset: int,
) -> SampleQueryRequest | None:
    """Build the request of an export. None means the export uses SQL.

    The export gets all samples in one request, so the request can use each sort.

    Raises:
        UnsupportedQueryError: If the transport is remote and cannot send the query.
    """
    try:
        query_expr = _to_image_query_expr(
            sample_type=sample_type,
            match_expression=match_expression,
            filters_sample_ids=filters_sample_ids,
        )
        sort = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=sample_type)
    except UnsupportedQueryError:
        if active_transport.is_remote():
            raise
        return None
    return SampleQueryRequest(query_expr=query_expr, sort=sort, offset=offset)


def build_evaluation_request(
    sample_type: SampleType,
    match_expression: MatchExpression | None,
    filters_sample_ids: bool,
    is_sliced: bool,
) -> SampleQueryRequest | None:
    """Build the request of an evaluation. None means the evaluation uses SQL.

    The order does not change the evaluated samples, so the request has only the filter.

    Raises:
        UnsupportedQueryError: If the transport is remote and cannot send the query.
    """
    if is_sliced:
        if active_transport.is_remote():
            raise UnsupportedQueryError("The transport cannot send the slice of an evaluation.")
        return None
    return build_export_request(
        sample_type=sample_type,
        match_expression=match_expression,
        order_by=[],
        filters_sample_ids=filters_sample_ids,
        offset=0,
    )


def iter_samples(
    collection_id: UUID, request: SampleQueryRequest, limit: int | None
) -> Iterator[RecordImageSample]:
    """Iterate over the samples of a query, one page at a time.

    Args:
        collection_id: The ID of the collection.
        request: The request of the first page.
        limit: The maximum number of samples. None gets all samples.
    """
    transport = active_transport.get_transport()
    remaining = limit
    while remaining is None or remaining > 0:
        page_size = DEFAULT_PAGE_SIZE if remaining is None else min(remaining, DEFAULT_PAGE_SIZE)
        request = request.model_copy(update={"limit": page_size})
        page = transport.samples.query(collection_id=collection_id, request=request)
        for record in page.samples:
            yield RecordImageSample(record=record, tag_transport=transport.tags)
        if page.next_cursor is None:
            return
        if remaining is not None:
            remaining -= len(page.samples)
        request = request.model_copy(update={"cursor": page.next_cursor, "offset": 0})


def _is_field_sort(key: SortKey | EvaluationMetricSortKey, table: str) -> bool:
    return isinstance(key, SortKey) and key.field.table == table


def _to_image_query_expr(
    sample_type: SampleType, match_expression: MatchExpression | None, filters_sample_ids: bool
) -> QueryExpr | None:
    if sample_type != SampleType.IMAGE or filters_sample_ids:
        raise UnsupportedQueryError("Only image queries without sample IDs are supported.")
    if match_expression is None:
        return None
    return query_expr_conversion.to_query_expr(
        match_expression=match_expression, sample_type=sample_type
    )
