"""Translate query expression models into dataset-query expressions.

Uses `isinstance` checks with `assert_never` to statically check that all cases are covered.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, TypeVar, Union

from typing_extensions import assert_never

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.classification_expression import (
    ClassificationField,
    ClassificationQuery,
)
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.instance_segmentation_expression import (
    InstanceSegmentationField,
    InstanceSegmentationQuery,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_expression import (
    ObjectDetectionField,
    ObjectDetectionQuery,
)
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.errors import QueryExprError
from lightly_studio.models.query_expr import (
    AndExpr,
    ClassificationMatchExpr,
    DatetimeExpr,
    EqualityComparisonOperator,
    EqualityFloatExpr,
    FieldRef,
    InstanceSegmentationMatchExpr,
    IntegerExpr,
    MatchExpr,
    NotExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    OrdinalFloatExpr,
    OrExpr,
    StringExpr,
    TagsContainsExpr,
)

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)
Number = Union[int, float]


class _EqualityField(Protocol[T_contra]):  # noqa: PLW1641
    """Field supporting equality comparisons that yield MatchExpression."""

    def __eq__(self, other: T_contra) -> MatchExpression: ...  # type: ignore[override]
    def __ne__(self, other: T_contra) -> MatchExpression: ...  # type: ignore[override]


class _OrdinalField(_EqualityField[T_contra], Protocol[T_contra]):
    """Field supporting ordinal comparisons that yield MatchExpression."""

    def __lt__(self, other: T_contra) -> MatchExpression: ...
    def __le__(self, other: T_contra) -> MatchExpression: ...
    def __gt__(self, other: T_contra) -> MatchExpression: ...
    def __ge__(self, other: T_contra) -> MatchExpression: ...


class _TagsAccessor(Protocol):
    """Tag accessor interface for dataset-query sample fields."""

    def contains(self, tag_name: str) -> MatchExpression: ...


# ---------------------------------------------------------------------------
# Field mappings: (table, name) → dataset-query field / accessor
# ---------------------------------------------------------------------------

_STRING_FIELDS: dict[tuple[str, str], _EqualityField[str]] = {
    ("image", "file_name"): ImageSampleField.file_name,
    ("image", "file_path_abs"): ImageSampleField.file_path_abs,
    ("video", "file_name"): VideoSampleField.file_name,
    ("video", "file_path_abs"): VideoSampleField.file_path_abs,
    ("classification", "label"): ClassificationField.label,
    ("object_detection", "label"): ObjectDetectionField.label,
    ("instance_segmentation", "label"): InstanceSegmentationField.label,
}

_INTEGER_FIELDS: dict[tuple[str, str], _OrdinalField[int]] = {
    ("image", "width"): ImageSampleField.width,
    ("image", "height"): ImageSampleField.height,
    ("video", "width"): VideoSampleField.width,
    ("video", "height"): VideoSampleField.height,
    ("object_detection", "x"): ObjectDetectionField.x,
    ("object_detection", "y"): ObjectDetectionField.y,
    ("object_detection", "width"): ObjectDetectionField.width,
    ("object_detection", "height"): ObjectDetectionField.height,
    ("instance_segmentation", "x"): InstanceSegmentationField.x,
    ("instance_segmentation", "y"): InstanceSegmentationField.y,
    ("instance_segmentation", "width"): InstanceSegmentationField.width,
    ("instance_segmentation", "height"): InstanceSegmentationField.height,
}

_DATETIME_FIELDS: dict[tuple[str, str], _OrdinalField[datetime]] = {
    ("image", "created_at"): ImageSampleField.created_at,
}

_ORDINAL_FLOAT_FIELDS: dict[tuple[str, str], _OrdinalField[Number]] = {
    ("video", "fps"): VideoSampleField.fps,
}

_EQUALITY_FLOAT_FIELDS: dict[tuple[str, str], _EqualityField[Number]] = {
    ("video", "duration_s"): VideoSampleField.duration_s,
}

_TAGS_FIELDS: dict[tuple[str, str], _TagsAccessor] = {
    ("image", "tags"): ImageSampleField.tags,
    ("video", "tags"): VideoSampleField.tags,
}


def _lookup(
    mapping: Mapping[tuple[str, str], T],
    field: FieldRef,
    type_: str,
) -> T:
    """Retrieve a dataset-query field / accessor with error handling.

    Args:
        mapping: Mapping from (table, name) to dataset-query field / accessor.
        field: Field reference from the query expression model.
        type_: String for error messages (e.g. "string", "ordinal float", etc.).
    """
    key = (field.table, field.name)
    if key not in mapping:
        raise QueryExprError(f"Unknown {type_} field: {field.table}.{field.name}")
    return mapping[key]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def to_match_expression(expr: MatchExpr) -> MatchExpression:  # noqa: PLR0911 C901
    """Translate a validated query-language expression to a dataset-query expression."""
    if isinstance(expr, StringExpr):
        return _apply_equality_operator(
            field=_lookup(mapping=_STRING_FIELDS, field=expr.field, type_="string"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, IntegerExpr):
        return _apply_ordinal_operator(
            field=_lookup(mapping=_INTEGER_FIELDS, field=expr.field, type_="integer"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, DatetimeExpr):
        return _apply_ordinal_operator(
            field=_lookup(mapping=_DATETIME_FIELDS, field=expr.field, type_="datetime"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, OrdinalFloatExpr):
        return _apply_ordinal_operator(
            field=_lookup(mapping=_ORDINAL_FLOAT_FIELDS, field=expr.field, type_="ordinal float"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, EqualityFloatExpr):
        return _apply_equality_operator(
            field=_lookup(mapping=_EQUALITY_FLOAT_FIELDS, field=expr.field, type_="equality float"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, TagsContainsExpr):
        accessor: _TagsAccessor = _lookup(mapping=_TAGS_FIELDS, field=expr.field, type_="tags")
        return accessor.contains(expr.tag_name)
    if isinstance(expr, ClassificationMatchExpr):
        return ClassificationQuery.match(to_match_expression(expr=expr.subexpr))
    if isinstance(expr, ObjectDetectionMatchExpr):
        return ObjectDetectionQuery.match(to_match_expression(expr=expr.subexpr))
    if isinstance(expr, InstanceSegmentationMatchExpr):
        return InstanceSegmentationQuery.match(to_match_expression(expr=expr.subexpr))
    if isinstance(expr, AndExpr):
        return AND(*(to_match_expression(expr=child) for child in expr.children))
    if isinstance(expr, OrExpr):
        return OR(*(to_match_expression(expr=child) for child in expr.children))
    if isinstance(expr, NotExpr):
        return NOT(to_match_expression(expr=expr.child))
    assert_never(expr)


def _apply_equality_operator(
    field: _EqualityField[T], operator: EqualityComparisonOperator, value: T
) -> MatchExpression:
    if operator is EqualityComparisonOperator.EQ:
        return field == value
    if operator is EqualityComparisonOperator.NEQ:
        return field != value
    assert_never(operator)


def _apply_ordinal_operator(
    field: _OrdinalField[T], operator: OrdinalComparisonOperator, value: T
) -> MatchExpression:
    if operator is OrdinalComparisonOperator.LT:
        return field < value
    if operator is OrdinalComparisonOperator.LTE:
        return field <= value
    if operator is OrdinalComparisonOperator.GT:
        return field > value
    if operator is OrdinalComparisonOperator.GTE:
        return field >= value
    if operator is OrdinalComparisonOperator.EQ:
        return field == value
    if operator is OrdinalComparisonOperator.NEQ:
        return field != value
    assert_never(operator)
