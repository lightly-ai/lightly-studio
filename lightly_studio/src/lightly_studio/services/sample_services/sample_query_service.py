"""Query the image samples of a collection, one page at a time.

Sorts on sample fields use keyset paging. Sorts on metadata or on evaluation metrics use offset
paging, because their values can be NULL or of mixed types. With offset paging, a page can skip
or repeat samples if samples change between the requests.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import ColumnElement, and_, or_
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.core.dataset_query import query_translation, sort_translation
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.errors import QueryExprError
from lightly_studio.models.image import ImageTable
from lightly_studio.models.query_expr import (
    ClassificationMatchExpr,
    FieldRef,
    ObjectDetectionMatchExpr,
    PolygonMatchExpr,
    QueryExpr,
    SegmentationMaskMatchExpr,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_query import (
    EvaluationMetricSortKey,
    ImageSampleRecord,
    SampleInclude,
    SamplePage,
    SampleQueryRequest,
    SortKey,
)
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import tag_resolver
from lightly_studio.services.sample_services import sample_query_cursor

# Only annotation match expressions correlate their table with the image.
_ANNOTATION_SCOPES: dict[type[BaseModel], str] = {
    ClassificationMatchExpr: "classification",
    ObjectDetectionMatchExpr: "object_detection",
    SegmentationMaskMatchExpr: "segmentation_mask",
    PolygonMatchExpr: "polygon",
}
_SORT_FIELDS = {"file_name", "file_path_abs", "created_at", "width", "height"}
_SUPPORTED_INCLUDES = {SampleInclude.TAGS}
_DEFAULT_SORT_KEY = SortKey(field=FieldRef(table="image", name="created_at"))


@dataclass(frozen=True)
class _SortColumn:
    name: str
    ascending: bool
    parse: Callable[[Any], Any]

    @property
    def column(self) -> Any:
        return col(getattr(ImageTable, self.name))


def query_samples(session: Session, collection_id: UUID, request: SampleQueryRequest) -> SamplePage:
    """Get one page of the image samples of a collection that match a request.

    Raises:
        ValueError: If the cursor is not valid or an include value is not supported.
        QueryExprError: If the filter or the sort uses an unknown field.
    """
    _check_includes(includes=request.include)
    hash_ = sample_query_cursor.query_hash(collection_id=collection_id, request=request)
    query = _filtered_query(collection_id=collection_id, request=request)
    if any(_needs_offset_paging(key=key) for key in request.sort):
        page, next_cursor = _offset_page(
            session=session, query=query, request=request, query_hash=hash_
        )
    else:
        page, next_cursor = _keyset_page(
            session=session, query=query, request=request, query_hash=hash_
        )
    sample_ids = [image.sample_id for image in page]
    tags = _tag_names(session=session, sample_ids=sample_ids, include=request.include)
    records = [_to_record(image=image, collection_id=collection_id, tags=tags) for image in page]
    return SamplePage(samples=records, next_cursor=next_cursor)


def get_sample_ids(
    session: Session, collection_id: UUID, request: SampleQueryRequest, limit: int | None
) -> list[UUID]:
    """Get the IDs of the image samples of a collection that match a request, in sort order.

    The IDs start after `request.offset` samples. `limit` sets the maximum number of IDs, and
    None gets all. The `cursor` and the `limit` of the request are not used.

    Raises:
        QueryExprError: If the filter or the sort uses an unknown field.
    """
    query = _filtered_query(collection_id=collection_id, request=request)
    for key in request.sort or [_DEFAULT_SORT_KEY]:
        query = _to_order_by(key=key).apply(query=query)
    query = query.order_by(col(SampleTable.sample_id))
    images = session.exec(query.offset(request.offset).limit(limit)).all()
    return [image.sample_id for image in images]


def _keyset_page(
    session: Session,
    query: SelectOfScalar[ImageTable],
    request: SampleQueryRequest,
    query_hash: str,
) -> tuple[Sequence[ImageTable], str | None]:
    sort_columns = _sort_columns(sort=request.sort)
    if request.cursor is not None:
        after = sample_query_cursor.decode(cursor=request.cursor, query_hash=query_hash)
        query = query.where(_after(sort_columns=sort_columns, values=after))
    query = query.order_by(*(c.column if c.ascending else c.column.desc() for c in sort_columns))
    offset = request.offset if request.cursor is None else 0
    images = session.exec(query.offset(offset).limit(request.limit + 1)).all()
    page = images[: request.limit]
    next_cursor = None
    if len(images) > request.limit:
        after = [getattr(page[-1], c.name) for c in sort_columns]
        next_cursor = sample_query_cursor.encode(query_hash=query_hash, after=after)
    return page, next_cursor


def _offset_page(
    session: Session,
    query: SelectOfScalar[ImageTable],
    request: SampleQueryRequest,
    query_hash: str,
) -> tuple[Sequence[ImageTable], str | None]:
    offset = request.offset
    if request.cursor is not None:
        offset = sample_query_cursor.decode_offset(cursor=request.cursor, query_hash=query_hash)
    for key in request.sort:
        query = _to_order_by(key=key).apply(query=query)
    # The sample ID breaks ties, as in the SQL path of the dataset query.
    query = query.order_by(col(SampleTable.sample_id))
    images = session.exec(query.offset(offset).limit(request.limit + 1)).all()
    page = images[: request.limit]
    next_cursor = None
    if len(images) > request.limit:
        next_offset = offset + len(page)
        next_cursor = sample_query_cursor.encode_offset(query_hash=query_hash, offset=next_offset)
    return page, next_cursor


def to_image_match_expression(query_expr: QueryExpr) -> MatchExpression:
    """Translate a query expression on image samples to a match expression.

    Raises:
        QueryExprError: If the expression uses a field that is not valid for images.
    """
    _check_filter_fields(value=query_expr, table="image")
    return query_translation.to_match_expression(expr=query_expr.match_expr)


def _filtered_query(collection_id: UUID, request: SampleQueryRequest) -> SelectOfScalar[ImageTable]:
    query = (
        select(ImageTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
    )
    if request.query_expr is None:
        return query
    match = to_image_match_expression(query_expr=request.query_expr)
    return query.where(match.get())


def _check_includes(includes: Sequence[SampleInclude]) -> None:
    for include in includes:
        if include not in _SUPPORTED_INCLUDES:
            raise ValueError(f"The include value '{include.value}' is not supported yet.")


def _check_filter_fields(value: object, table: str) -> None:
    """Reject fields of tables that are not in the scope of the expression."""
    if isinstance(value, FieldRef):
        if value.table != table:
            raise QueryExprError(f"The field {value.table}.{value.name} is not valid here.")
        return
    if isinstance(value, BaseModel):
        scope = _ANNOTATION_SCOPES.get(type(value), table)
        for child in vars(value).values():
            _check_filter_fields(value=child, table=scope)
    elif isinstance(value, list):
        for child in value:
            _check_filter_fields(value=child, table=table)


def _sort_columns(sort: Sequence[SortKey | EvaluationMetricSortKey]) -> list[_SortColumn]:
    keys = sort or [_DEFAULT_SORT_KEY]
    columns = []
    for key in keys:
        field = _keyset_sort_field(key=key)
        parse = _CURSOR_PARSERS[field.name]
        ascending = key.direction == SortDirection.asc
        columns.append(_SortColumn(name=field.name, ascending=ascending, parse=parse))
    # The sample ID breaks ties, so the order is total and no sample is skipped.
    columns.append(_SortColumn(name="sample_id", ascending=True, parse=_parse_uuid))
    return columns


def _keyset_sort_field(key: SortKey | EvaluationMetricSortKey) -> FieldRef:
    """Get the field of a sort key that keyset paging can use."""
    if isinstance(key, EvaluationMetricSortKey):
        raise QueryExprError("Keyset paging cannot sort by an evaluation metric.")
    if key.field.table != "image" or key.field.name not in _SORT_FIELDS:
        raise QueryExprError(f"Unknown sort field: {key.field.table}.{key.field.name}")
    return key.field


def _needs_offset_paging(key: SortKey | EvaluationMetricSortKey) -> bool:
    return isinstance(key, EvaluationMetricSortKey) or key.field.table == "metadata"


def _to_order_by(key: SortKey | EvaluationMetricSortKey) -> OrderByExpression:
    if isinstance(key, EvaluationMetricSortKey):
        return sort_translation.evaluation_metric_sort_to_order_by(
            evaluation_run_name=key.run_name, metric_name=key.metric_name, direction=key.direction
        )
    if key.field.table not in {"image", "metadata"}:
        raise QueryExprError(f"Unknown sort field: {key.field.table}.{key.field.name}")
    return sort_translation.sort_to_order_by(
        key=(key.field.table, key.field.name), direction=key.direction
    )


def _after(sort_columns: Sequence[_SortColumn], values: Sequence[Any]) -> ColumnElement[bool]:
    """Match the rows that come after `values` in the sort order."""
    if len(values) != len(sort_columns):
        raise ValueError("The cursor is not valid.")
    try:
        parsed = [c.parse(value) for c, value in zip(sort_columns, values)]
    except (TypeError, ValueError) as error:
        raise ValueError("The cursor is not valid.") from error
    clauses = []
    for index, sort_column in enumerate(sort_columns):
        equal = [c.column == v for c, v in zip(sort_columns[:index], parsed[:index])]
        value = parsed[index]
        beyond = sort_column.column > value if sort_column.ascending else sort_column.column < value
        clauses.append(and_(*equal, beyond))
    return or_(*clauses)


def _tag_names(
    session: Session, sample_ids: Sequence[UUID], include: Sequence[SampleInclude]
) -> dict[UUID, list[str]] | None:
    if SampleInclude.TAGS not in include:
        return None
    return tag_resolver.get_names_by_sample_ids(session=session, sample_ids=sample_ids)


def _to_record(
    image: ImageTable, collection_id: UUID, tags: dict[UUID, list[str]] | None
) -> ImageSampleRecord:
    sample_tags = None if tags is None else tags.get(image.sample_id, [])
    return ImageSampleRecord(**image.model_dump(), collection_id=collection_id, tags=sample_tags)


def _parse_int(value: Any) -> int:
    if type(value) is not int:
        raise TypeError("The cursor value is not an integer.")
    return value


def _parse_str(value: Any) -> str:
    if not isinstance(value, str):
        raise TypeError("The cursor value is not a string.")
    return value


def _parse_uuid(value: Any) -> UUID:
    return UUID(_parse_str(value=value))


_CURSOR_PARSERS: dict[str, Callable[[Any], Any]] = {
    "file_name": _parse_str,
    "file_path_abs": _parse_str,
    "created_at": datetime.fromisoformat,
    "width": _parse_int,
    "height": _parse_int,
}
