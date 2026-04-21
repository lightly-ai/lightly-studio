"""Translate query-language models into dataset-query expressions."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol, TypeVar, Union

from typing_extensions import assert_never

from lightly_studio.core.dataset_query import (
    AND,
    NOT,
    OR,
    ClassificationField,
    ClassificationQuery,
    ImageSampleField,
    InstanceSegmentationField,
    InstanceSegmentationQuery,
    ObjectDetectionField,
    ObjectDetectionQuery,
    VideoSampleField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.query_language import models

T = TypeVar("T")
T_contra = TypeVar("T_contra", contravariant=True)
Number = Union[int, float]


class EqualityField(Protocol[T_contra]):
    """Field supporting equality comparisons that yield MatchExpression."""

    def __eq__(self, other: T_contra) -> MatchExpression: ...  # type: ignore[override]
    def __ne__(self, other: T_contra) -> MatchExpression: ...  # type: ignore[override]


class OrdinalField(EqualityField[T_contra], Protocol[T_contra]):
    """Field supporting ordinal comparisons that yield MatchExpression."""

    def __lt__(self, other: T_contra) -> MatchExpression: ...
    def __le__(self, other: T_contra) -> MatchExpression: ...
    def __gt__(self, other: T_contra) -> MatchExpression: ...
    def __ge__(self, other: T_contra) -> MatchExpression: ...


class TagsAccessor(Protocol):
    """Tag accessor interface for dataset-query sample fields."""

    def contains(self, tag_name: str) -> MatchExpression: ...


# ---------------------------------------------------------------------------
# Field mappings: (table, name) → dataset-query field / accessor
# ---------------------------------------------------------------------------

_STRING_FIELDS: dict[tuple[str, str], EqualityField[str]] = {
    ("image", "file_name"): ImageSampleField.file_name,
    ("image", "file_path_abs"): ImageSampleField.file_path_abs,
    ("video", "file_name"): VideoSampleField.file_name,
    ("video", "file_path_abs"): VideoSampleField.file_path_abs,
}

_INTEGER_FIELDS: dict[tuple[str, str], OrdinalField[int]] = {
    ("image", "width"): ImageSampleField.width,
    ("image", "height"): ImageSampleField.height,
    ("video", "width"): VideoSampleField.width,
    ("video", "height"): VideoSampleField.height,
}

_DATETIME_FIELDS: dict[tuple[str, str], OrdinalField[datetime]] = {
    ("image", "created_at"): ImageSampleField.created_at,
}

_ORDINAL_FLOAT_FIELDS: dict[tuple[str, str], OrdinalField[Number]] = {
    ("video", "fps"): VideoSampleField.fps,
}

_EQUALITY_FLOAT_FIELDS: dict[tuple[str, str], EqualityField[Number]] = {
    ("video", "duration_s"): VideoSampleField.duration_s,
}

_TAGS_FIELDS: dict[tuple[str, str], TagsAccessor] = {
    ("image", "tags"): ImageSampleField.tags,
    ("video", "tags"): VideoSampleField.tags,
}

_ANNOTATION_LABEL_FIELDS: dict[tuple[str, str], EqualityField[str]] = {
    ("classification", "label"): ClassificationField.label,
    ("object_detection", "label"): ObjectDetectionField.label,
    ("instance_segmentation", "label"): InstanceSegmentationField.label,
}

_ANNOTATION_GEOMETRY_FIELDS: dict[tuple[str, str], OrdinalField[Number]] = {
    ("object_detection", "x"): ObjectDetectionField.x,
    ("object_detection", "y"): ObjectDetectionField.y,
    ("object_detection", "width"): ObjectDetectionField.width,
    ("object_detection", "height"): ObjectDetectionField.height,
    ("instance_segmentation", "x"): InstanceSegmentationField.x,
    ("instance_segmentation", "y"): InstanceSegmentationField.y,
    ("instance_segmentation", "width"): InstanceSegmentationField.width,
    ("instance_segmentation", "height"): InstanceSegmentationField.height,
}


def _lookup(
    mapping: dict[tuple[str, str], Any],
    table: str,
    name: str,
    kind: str,
) -> Any:
    key = (table, name)
    if key not in mapping:
        raise ValueError(f"Unknown {kind} field: {table}.{name}")
    return mapping[key]


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def to_match_expression(expr: models.MatchExpr) -> MatchExpression:
    """Translate a validated query-language expression to a dataset-query expression."""
    if isinstance(expr, models.StringExpr):
        return _apply_equality_operator(
            field=_lookup(_STRING_FIELDS, expr.field.table, expr.field.name, "string"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, models.IntegerExpr):
        return _apply_ordinal_operator(
            field=_lookup(_INTEGER_FIELDS, expr.field.table, expr.field.name, "integer"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, models.DatetimeExpr):
        return _apply_ordinal_operator(
            field=_lookup(_DATETIME_FIELDS, expr.field.table, expr.field.name, "datetime"),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, models.OrdinalFloatExpr):
        return _apply_ordinal_operator(
            field=_lookup(
                _ORDINAL_FLOAT_FIELDS, expr.field.table, expr.field.name, "ordinal float"
            ),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, models.EqualityFloatExpr):
        return _apply_equality_operator(
            field=_lookup(
                _EQUALITY_FLOAT_FIELDS, expr.field.table, expr.field.name, "equality float"
            ),
            operator=expr.operator,
            value=expr.value,
        )
    if isinstance(expr, models.TagsContainsExpr):
        accessor: TagsAccessor = _lookup(
            _TAGS_FIELDS, expr.field.table, expr.field.name, "tags"
        )
        return accessor.contains(expr.tag_name)
    if isinstance(expr, models.ClassificationMatchExpr):
        criteria = [_translate_annotation_label_criterion(c) for c in expr.criteria]
        return ClassificationQuery.match(*criteria)
    if isinstance(expr, models.ObjectDetectionMatchExpr):
        criteria = [_translate_annotation_criterion(c) for c in expr.criteria]
        return ObjectDetectionQuery.match(*criteria)
    if isinstance(expr, models.InstanceSegmentationMatchExpr):
        criteria = [_translate_annotation_criterion(c) for c in expr.criteria]
        return InstanceSegmentationQuery.match(*criteria)
    if isinstance(expr, models.AndExpr):
        return AND(*(to_match_expression(child) for child in expr.children))
    if isinstance(expr, models.OrExpr):
        return OR(*(to_match_expression(child) for child in expr.children))
    if isinstance(expr, models.NotExpr):
        return NOT(to_match_expression(expr.child))
    assert_never(expr)


def _translate_annotation_label_criterion(
    expr: models.AnnotationLabelExpr,
) -> MatchExpression:
    return _apply_equality_operator(
        field=_lookup(
            _ANNOTATION_LABEL_FIELDS, expr.field.table, expr.field.name, "annotation label"
        ),
        operator=expr.operator,
        value=expr.value,
    )


def _translate_annotation_criterion(
    expr: models.AnnotationLabelExpr | models.AnnotationGeometryExpr,
) -> MatchExpression:
    if isinstance(expr, models.AnnotationLabelExpr):
        return _translate_annotation_label_criterion(expr)
    if isinstance(expr, models.AnnotationGeometryExpr):
        return _apply_ordinal_operator(
            field=_lookup(
                _ANNOTATION_GEOMETRY_FIELDS,
                expr.field.table,
                expr.field.name,
                "annotation geometry",
            ),
            operator=expr.operator,
            value=expr.value,
        )
    assert_never(expr)


def _apply_equality_operator(
    *, field: EqualityField[T], operator: models.EqualityComparisonOperator, value: T
) -> MatchExpression:
    if operator is models.EqualityComparisonOperator.EQ:
        return field == value
    if operator is models.EqualityComparisonOperator.NEQ:
        return field != value
    assert_never(operator)


def _apply_ordinal_operator(
    *, field: OrdinalField[T], operator: models.OrdinalComparisonOperator, value: T
) -> MatchExpression:
    if operator is models.OrdinalComparisonOperator.LT:
        return field < value
    if operator is models.OrdinalComparisonOperator.LTE:
        return field <= value
    if operator is models.OrdinalComparisonOperator.GT:
        return field > value
    if operator is models.OrdinalComparisonOperator.GTE:
        return field >= value
    if operator is models.OrdinalComparisonOperator.EQ:
        return field == value
    if operator is models.OrdinalComparisonOperator.NEQ:
        return field != value
    assert_never(operator)
