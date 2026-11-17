"""Query the image samples of a collection, one page at a time."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.errors import QueryExprError
from lightly_studio.models.image import ImageTable
from lightly_studio.models.query_expr import (
    ClassificationMatchExpr,
    FieldRef,
    ObjectDetectionMatchExpr,
    SegmentationMaskMatchExpr,
)
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sample_query import (
    ImageSampleRecord,
    SampleInclude,
    SamplePage,
    SampleQueryRequest,
    SortKey,
)
from lightly_studio.models.sort_direction import SortDirection

# Only annotation match expressions correlate their table with the image.
_ANNOTATION_SCOPES: dict[type[BaseModel], str] = {
    ClassificationMatchExpr: "classification",
    ObjectDetectionMatchExpr: "object_detection",
    SegmentationMaskMatchExpr: "segmentation_mask",
}
_SORT_FIELDS = {"file_name", "file_path_abs", "created_at", "width", "height"}
_SUPPORTED_INCLUDES: set[SampleInclude] = set()


@dataclass(frozen=True)
class _SortColumn:
    name: str
    ascending: bool

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
    if request.cursor is not None:
        raise ValueError("Paging with a cursor is not supported yet.")
    sort_columns = _sort_columns(sort=request.sort)
    query = _filtered_query(collection_id=collection_id, request=request)
    query = query.order_by(*(c.column if c.ascending else c.column.desc() for c in sort_columns))
    images = session.exec(query.offset(request.offset).limit(request.limit)).all()
    records = [_to_record(image=image, collection_id=collection_id) for image in images]
    return SamplePage(samples=records)


def _filtered_query(collection_id: UUID, request: SampleQueryRequest) -> SelectOfScalar[ImageTable]:
    query = (
        select(ImageTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(SampleTable.collection_id == collection_id)
    )
    if request.query_expr is None:
        return query
    _check_filter_fields(value=request.query_expr, table="image")
    match = query_translation.to_match_expression(expr=request.query_expr.match_expr)
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


def _sort_columns(sort: Sequence[SortKey]) -> list[_SortColumn]:
    keys = sort or [SortKey(field=FieldRef(table="image", name="created_at"))]
    columns = []
    for key in keys:
        if key.field.table != "image" or key.field.name not in _SORT_FIELDS:
            raise QueryExprError(f"Unknown sort field: {key.field.table}.{key.field.name}")
        ascending = key.direction == SortDirection.asc
        columns.append(_SortColumn(name=key.field.name, ascending=ascending))
    # The sample ID breaks ties, so the order is total and no sample is skipped.
    columns.append(_SortColumn(name="sample_id", ascending=True))
    return columns


def _to_record(image: ImageTable, collection_id: UUID) -> ImageSampleRecord:
    return ImageSampleRecord(**image.model_dump(), collection_id=collection_id)
