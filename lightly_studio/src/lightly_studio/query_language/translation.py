"""Translate query-language models into dataset-query expressions."""

from __future__ import annotations

from datetime import datetime
from functools import singledispatch
from typing import Protocol, TypeVar, Union

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


@singledispatch
def to_match_expression(expr: models.MatchExpr) -> MatchExpression:
    """Translate a validated query-language expression to a dataset-query expression."""
    raise ValueError(f"Unsupported query expression type: {type(expr).__name__}")


@to_match_expression.register
def _string_expr(expr: models.StringExpr) -> MatchExpression:
    return _apply_equality_operator(
        field=_get_string_field(expr.field),
        operator=expr.operator,
        value=expr.value,
    )


@to_match_expression.register
def _integer_expr(expr: models.IntegerExpr) -> MatchExpression:
    return _apply_ordinal_operator(
        field=_get_integer_field(expr.field),
        operator=expr.operator,
        value=expr.value,
    )


@to_match_expression.register
def _datetime_expr(expr: models.DatetimeExpr) -> MatchExpression:
    return _apply_ordinal_operator(
        field=_get_datetime_field(expr.field),
        operator=expr.operator,
        value=expr.value,
    )


@to_match_expression.register
def _ordinal_float_expr(expr: models.OrdinalFloatExpr) -> MatchExpression:
    return _apply_ordinal_operator(
        field=_get_ordinal_float_field(expr.field),
        operator=expr.operator,
        value=expr.value,
    )


@to_match_expression.register
def _equality_float_expr(expr: models.EqualityFloatExpr) -> MatchExpression:
    return _apply_equality_operator(
        field=_get_equality_float_field(expr.field),
        operator=expr.operator,
        value=expr.value,
    )


@to_match_expression.register
def _tags_contains_expr(expr: models.TagsContainsExpr) -> MatchExpression:
    return _get_tags_accessor(expr.field).contains(expr.tag_name)


@to_match_expression.register
def _classification_match_expr(expr: models.ClassificationMatchExpr) -> MatchExpression:
    criteria = [_translate_classification_criterion(c) for c in expr.criteria]
    return ClassificationQuery.match(*criteria)


@to_match_expression.register
def _object_detection_match_expr(expr: models.ObjectDetectionMatchExpr) -> MatchExpression:
    criteria = [_translate_object_detection_criterion(c) for c in expr.criteria]
    return ObjectDetectionQuery.match(*criteria)


@to_match_expression.register
def _instance_segmentation_match_expr(
    expr: models.InstanceSegmentationMatchExpr,
) -> MatchExpression:
    criteria = [_translate_instance_segmentation_criterion(c) for c in expr.criteria]
    return InstanceSegmentationQuery.match(*criteria)


@to_match_expression.register
def _and_expr(expr: models.AndExpr) -> MatchExpression:
    return AND(*(to_match_expression(child) for child in expr.children))


@to_match_expression.register
def _or_expr(expr: models.OrExpr) -> MatchExpression:
    return OR(*(to_match_expression(child) for child in expr.children))


@to_match_expression.register
def _not_expr(expr: models.NotExpr) -> MatchExpression:
    return NOT(to_match_expression(expr.child))


def _translate_classification_criterion(expr: models.AnnotationLabelExpr) -> MatchExpression:
    if expr.field.table != "classification":
        raise ValueError(f"Classification criteria require classification fields, got {expr.field}")
    return _apply_equality_operator(
        field=ClassificationField.label,
        operator=expr.operator,
        value=expr.value,
    )


def _translate_object_detection_criterion(expr: models.ObjectDetectionExpr) -> MatchExpression:
    if isinstance(expr, models.AnnotationLabelExpr):
        if expr.field.table != "object_detection":
            raise ValueError(
                "Object detection label criteria require object_detection fields, "
                f"got {expr.field}"
            )
        return _apply_equality_operator(
            field=ObjectDetectionField.label,
            operator=expr.operator,
            value=expr.value,
        )
    if expr.field.table != "object_detection":
        raise ValueError(
            "Object detection geometry criteria require object_detection fields, "
            f"got {expr.field}"
        )
    return _apply_ordinal_operator(
        field=_get_object_detection_geometry_field(expr.field.name),
        operator=expr.operator,
        value=expr.value,
    )


def _translate_instance_segmentation_criterion(
    expr: models.InstanceSegmentationExpr,
) -> MatchExpression:
    if isinstance(expr, models.AnnotationLabelExpr):
        if expr.field.table != "instance_segmentation":
            raise ValueError(
                "Instance segmentation label criteria require instance_segmentation fields, "
                f"got {expr.field}"
            )
        return _apply_equality_operator(
            field=InstanceSegmentationField.label,
            operator=expr.operator,
            value=expr.value,
        )
    if expr.field.table != "instance_segmentation":
        raise ValueError(
            "Instance segmentation geometry criteria require instance_segmentation fields, "
            f"got {expr.field}"
        )
    return _apply_ordinal_operator(
        field=_get_instance_segmentation_geometry_field(expr.field.name),
        operator=expr.operator,
        value=expr.value,
    )


@singledispatch
def _get_string_field(field: models.StringFieldRef) -> EqualityField[str]:
    raise ValueError(f"Unsupported string field ref type: {type(field).__name__}")


@_get_string_field.register
def _get_image_string_field(field: models.ImageStringFieldRef) -> EqualityField[str]:
    name = field.name
    if name is models.ImageStringFieldName.FILE_NAME:
        return ImageSampleField.file_name
    if name is models.ImageStringFieldName.FILE_PATH_ABS:
        return ImageSampleField.file_path_abs
    assert_never(name)


@_get_string_field.register
def _get_video_string_field(field: models.VideoStringFieldRef) -> EqualityField[str]:
    name = field.name
    if name is models.VideoStringFieldName.FILE_NAME:
        return VideoSampleField.file_name
    if name is models.VideoStringFieldName.FILE_PATH_ABS:
        return VideoSampleField.file_path_abs
    assert_never(name)


@singledispatch
def _get_integer_field(field: models.IntegerFieldRef) -> OrdinalField[int]:
    raise ValueError(f"Unsupported integer field ref type: {type(field).__name__}")


@_get_integer_field.register
def _get_image_integer_field(field: models.ImageIntegerFieldRef) -> OrdinalField[int]:
    name = field.name
    if name is models.ImageIntegerFieldName.WIDTH:
        return ImageSampleField.width
    if name is models.ImageIntegerFieldName.HEIGHT:
        return ImageSampleField.height
    assert_never(name)


@_get_integer_field.register
def _get_video_integer_field(field: models.VideoIntegerFieldRef) -> OrdinalField[int]:
    name = field.name
    if name is models.VideoIntegerFieldName.WIDTH:
        return VideoSampleField.width
    if name is models.VideoIntegerFieldName.HEIGHT:
        return VideoSampleField.height
    assert_never(name)


@singledispatch
def _get_datetime_field(field: models.DatetimeFieldRef) -> OrdinalField[datetime]:
    raise ValueError(f"Unsupported datetime field ref type: {type(field).__name__}")


@_get_datetime_field.register
def _get_image_datetime_field(field: models.ImageDatetimeFieldRef) -> OrdinalField[datetime]:
    name = field.name
    if name is models.ImageDatetimeFieldName.CREATED_AT:
        return ImageSampleField.created_at
    assert_never(name)


@singledispatch
def _get_ordinal_float_field(field: models.OrdinalFloatFieldRef) -> OrdinalField[Number]:
    raise ValueError(f"Unsupported ordinal float field ref type: {type(field).__name__}")


@_get_ordinal_float_field.register
def _get_video_ordinal_float_field(
    field: models.VideoOrdinalFloatFieldRef,
) -> OrdinalField[Number]:
    name = field.name
    if name is models.VideoFloatFieldName.FPS:
        return VideoSampleField.fps
    assert_never(name)


@singledispatch
def _get_equality_float_field(field: models.EqualityFloatFieldRef) -> EqualityField[Number]:
    raise ValueError(f"Unsupported equality float field ref type: {type(field).__name__}")


@_get_equality_float_field.register
def _get_video_equality_float_field(
    field: models.VideoEqualityFloatFieldRef,
) -> EqualityField[Number]:
    name = field.name
    if name is models.VideoEqualityFloatFieldName.DURATION_S:
        return VideoSampleField.duration_s
    assert_never(name)


@singledispatch
def _get_tags_accessor(field: models.TagsFieldRef) -> TagsAccessor:
    raise ValueError(f"Unsupported tags field ref type: {type(field).__name__}")


@_get_tags_accessor.register
def _get_image_tags_accessor(field: models.ImageTagsFieldRef) -> TagsAccessor:
    return ImageSampleField.tags


@_get_tags_accessor.register
def _get_video_tags_accessor(field: models.VideoTagsFieldRef) -> TagsAccessor:
    return VideoSampleField.tags


def _get_object_detection_geometry_field(
    name: models.AnnotationGeometryFieldName,
) -> OrdinalField[Number]:
    if name is models.AnnotationGeometryFieldName.X:
        return ObjectDetectionField.x
    if name is models.AnnotationGeometryFieldName.Y:
        return ObjectDetectionField.y
    if name is models.AnnotationGeometryFieldName.WIDTH:
        return ObjectDetectionField.width
    if name is models.AnnotationGeometryFieldName.HEIGHT:
        return ObjectDetectionField.height
    assert_never(name)


def _get_instance_segmentation_geometry_field(
    name: models.AnnotationGeometryFieldName,
) -> OrdinalField[Number]:
    if name is models.AnnotationGeometryFieldName.X:
        return InstanceSegmentationField.x
    if name is models.AnnotationGeometryFieldName.Y:
        return InstanceSegmentationField.y
    if name is models.AnnotationGeometryFieldName.WIDTH:
        return InstanceSegmentationField.width
    if name is models.AnnotationGeometryFieldName.HEIGHT:
        return InstanceSegmentationField.height
    assert_never(name)


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
