"""Translate query-language models into dataset-query expressions."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, TypeVar, Union

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


def to_match_expression(expr: models.MatchExpr) -> MatchExpression:
    """Translate a validated query-language expression to a dataset-query expression."""
    if isinstance(expr, models.StringExpr):
        return _apply_equality_operator(
            field=_get_string_field(expr.field),
            operator=expr.operator.value,
            value=expr.value,
        )
    if isinstance(expr, models.IntegerExpr):
        return _apply_ordinal_operator(
            field=_get_integer_field(expr.field),
            operator=expr.operator.value,
            value=expr.value,
        )
    if isinstance(expr, models.DatetimeExpr):
        return _apply_ordinal_operator(
            field=_get_datetime_field(expr.field),
            operator=expr.operator.value,
            value=expr.value,
        )
    if isinstance(expr, models.OrdinalFloatExpr):
        return _apply_ordinal_operator(
            field=_get_ordinal_float_field(expr.field),
            operator=expr.operator.value,
            value=expr.value,
        )
    if isinstance(expr, models.EqualityFloatExpr):
        return _apply_equality_operator(
            field=_get_equality_float_field(expr.field),
            operator=expr.operator.value,
            value=expr.value,
        )
    if isinstance(expr, models.TagsContainsExpr):
        return _get_tags_accessor(expr.field).contains(expr.tag_name)
    if isinstance(expr, models.ClassificationMatchExpr):
        criteria = [_translate_classification_criterion(criterion) for criterion in expr.criteria]
        return ClassificationQuery.match(*criteria)
    if isinstance(expr, models.ObjectDetectionMatchExpr):
        criteria = [_translate_object_detection_criterion(criterion) for criterion in expr.criteria]
        return ObjectDetectionQuery.match(*criteria)
    if isinstance(expr, models.InstanceSegmentationMatchExpr):
        criteria = [
            _translate_instance_segmentation_criterion(criterion) for criterion in expr.criteria
        ]
        return InstanceSegmentationQuery.match(*criteria)
    if isinstance(expr, models.AndExpr):
        return AND(*(to_match_expression(child) for child in expr.children))
    if isinstance(expr, models.OrExpr):
        return OR(*(to_match_expression(child) for child in expr.children))
    if isinstance(expr, models.NotExpr):
        return NOT(to_match_expression(expr.child))
    raise ValueError(f"Unsupported query expression type: {type(expr).__name__}")


def _translate_classification_criterion(expr: models.AnnotationLabelExpr) -> MatchExpression:
    if expr.field.table != "classification":
        raise ValueError(f"Classification criteria require classification fields, got {expr.field}")
    return _apply_equality_operator(
        field=ClassificationField.label,
        operator=expr.operator.value,
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
            operator=expr.operator.value,
            value=expr.value,
        )
    if expr.field.table != "object_detection":
        raise ValueError(
            "Object detection geometry criteria require object_detection fields, "
            f"got {expr.field}"
        )
    return _apply_ordinal_operator(
        field=_get_object_detection_geometry_field(expr.field.name),
        operator=expr.operator.value,
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
            operator=expr.operator.value,
            value=expr.value,
        )
    if expr.field.table != "instance_segmentation":
        raise ValueError(
            "Instance segmentation geometry criteria require instance_segmentation fields, "
            f"got {expr.field}"
        )
    return _apply_ordinal_operator(
        field=_get_instance_segmentation_geometry_field(expr.field.name),
        operator=expr.operator.value,
        value=expr.value,
    )


def _get_string_field(field: models.StringFieldRef) -> EqualityField[str]:
    if field.table == "image":
        return {
            models.ImageStringFieldName.FILE_NAME: ImageSampleField.file_name,
            models.ImageStringFieldName.FILE_PATH_ABS: ImageSampleField.file_path_abs,
        }[field.name]
    return {
        models.VideoStringFieldName.FILE_NAME: VideoSampleField.file_name,
        models.VideoStringFieldName.FILE_PATH_ABS: VideoSampleField.file_path_abs,
    }[field.name]


def _get_integer_field(field: models.IntegerFieldRef) -> OrdinalField[int]:
    if field.table == "image":
        return {
            models.ImageIntegerFieldName.WIDTH: ImageSampleField.width,
            models.ImageIntegerFieldName.HEIGHT: ImageSampleField.height,
        }[field.name]
    return {
        models.VideoIntegerFieldName.WIDTH: VideoSampleField.width,
        models.VideoIntegerFieldName.HEIGHT: VideoSampleField.height,
    }[field.name]


def _get_datetime_field(field: models.DatetimeFieldRef) -> OrdinalField[datetime]:
    return {
        models.ImageDatetimeFieldName.CREATED_AT: ImageSampleField.created_at,
    }[field.name]


def _get_ordinal_float_field(field: models.OrdinalFloatFieldRef) -> OrdinalField[Number]:
    return {
        models.VideoFloatFieldName.FPS: VideoSampleField.fps,
    }[field.name]


def _get_equality_float_field(field: models.EqualityFloatFieldRef) -> EqualityField[Number]:
    return {
        models.VideoEqualityFloatFieldName.DURATION_S: VideoSampleField.duration_s,
    }[field.name]


def _get_tags_accessor(field: models.TagsFieldRef) -> TagsAccessor:
    if field.table == "image":
        return ImageSampleField.tags
    return VideoSampleField.tags


def _get_object_detection_geometry_field(
    name: models.AnnotationGeometryFieldName,
) -> OrdinalField[Number]:
    return {
        models.AnnotationGeometryFieldName.X: ObjectDetectionField.x,
        models.AnnotationGeometryFieldName.Y: ObjectDetectionField.y,
        models.AnnotationGeometryFieldName.WIDTH: ObjectDetectionField.width,
        models.AnnotationGeometryFieldName.HEIGHT: ObjectDetectionField.height,
    }[name]


def _get_instance_segmentation_geometry_field(
    name: models.AnnotationGeometryFieldName,
) -> OrdinalField[Number]:
    return {
        models.AnnotationGeometryFieldName.X: InstanceSegmentationField.x,
        models.AnnotationGeometryFieldName.Y: InstanceSegmentationField.y,
        models.AnnotationGeometryFieldName.WIDTH: InstanceSegmentationField.width,
        models.AnnotationGeometryFieldName.HEIGHT: InstanceSegmentationField.height,
    }[name]


def _apply_equality_operator(
    *, field: EqualityField[T], operator: str, value: T
) -> MatchExpression:
    operations = {
        "==": lambda: field == value,
        "!=": lambda: field != value,
    }
    try:
        return operations[operator]()
    except KeyError as exc:
        raise ValueError(f"Unsupported equality operator: {operator}") from exc


def _apply_ordinal_operator(
    *, field: OrdinalField[T], operator: str, value: T
) -> MatchExpression:
    operations = {
        "<": lambda: field < value,
        "<=": lambda: field <= value,
        ">": lambda: field > value,
        ">=": lambda: field >= value,
        "==": lambda: field == value,
        "!=": lambda: field != value,
    }
    try:
        return operations[operator]()
    except KeyError as exc:
        raise ValueError(f"Unsupported ordinal operator: {operator}") from exc
