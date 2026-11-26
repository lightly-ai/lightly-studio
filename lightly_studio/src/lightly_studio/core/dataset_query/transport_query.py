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
from lightly_studio.models.sample_query import (
    DEFAULT_PAGE_SIZE,
    SampleInclude,
    SampleQueryRequest,
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
        if sample_type != SampleType.IMAGE or filters_sample_ids:
            raise UnsupportedQueryError("Only image queries without sample IDs are supported.")
        query_expr = (
            None
            if match_expression is None
            else query_expr_conversion.to_query_expr(
                match_expression=match_expression, sample_type=sample_type
            )
        )
        sort = query_expr_conversion.to_sort_keys(order_by=order_by, sample_type=sample_type)
        # TODO(iunir, 11/2026): Remove when the server pages metadata sorts.
        if any(key.field.table != sample_type.value for key in sort):
            raise UnsupportedQueryError("The server cannot page this sort yet.")
    except UnsupportedQueryError:
        if active_transport.is_remote():
            raise
        return None
    return SampleQueryRequest(
        query_expr=query_expr, sort=sort, offset=offset, include=[SampleInclude.TAGS]
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
