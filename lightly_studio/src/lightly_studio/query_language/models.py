"""Pydantic models for the query tree used in GUI-based querying."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr


class EqualityComparisonOperator(str, Enum):
    """Operators supported by equality-only fields."""

    EQ = "=="
    NEQ = "!="


class OrdinalComparisonOperator(str, Enum):
    """Operators supported by ordinal fields."""

    EQ = "=="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="


class ImageStringField(str, Enum):
    """String image fields supported by the current query engine."""

    FILE_NAME = "file_name"
    FILE_PATH_ABS = "file_path_abs"


class ImageIntegerField(str, Enum):
    """Integer image fields supported by the current query engine."""

    WIDTH = "width"
    HEIGHT = "height"


class ImageDatetimeField(str, Enum):
    """Datetime image fields supported by the current query engine."""

    CREATED_AT = "created_at"


class VideoStringField(str, Enum):
    """String video fields supported by the current query engine."""

    FILE_NAME = "file_name"
    FILE_PATH_ABS = "file_path_abs"


class VideoIntegerField(str, Enum):
    """Integer video fields supported by the current query engine."""

    WIDTH = "width"
    HEIGHT = "height"


class VideoFloatField(str, Enum):
    """Float video fields with full ordinal comparisons."""

    FPS = "fps"


class VideoEqualityFloatField(str, Enum):
    """Float video fields limited by the current query engine to equality checks."""

    DURATION_S = "duration_s"


class AnnotationLabelField(str, Enum):
    """Annotation string fields supported by the current query engine."""

    LABEL = "label"


class AnnotationGeometryField(str, Enum):
    """Annotation numeric fields supported by the current query engine."""

    X = "x"
    Y = "y"
    WIDTH = "width"
    HEIGHT = "height"


StringField = Union[ImageStringField, VideoStringField]
IntegerField = Union[ImageIntegerField, VideoIntegerField]
DatetimeField = ImageDatetimeField
FloatField = VideoFloatField
EqualityFloatField = VideoEqualityFloatField


class StringExpression(BaseModel):
    """Leaf node for equality comparisons on string sample fields."""

    type: Literal["string_field_comparison"] = "string_field_comparison"
    field: StringField
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerExpression(BaseModel):
    """Leaf node for ordinal comparisons on integer sample fields."""

    type: Literal["integer_field_comparison"] = "integer_field_comparison"
    field: IntegerField
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeExpression(BaseModel):
    """Leaf node for ordinal comparisons on datetime sample fields."""

    type: Literal["datetime_field_comparison"] = "datetime_field_comparison"
    field: DatetimeField
    operator: OrdinalComparisonOperator
    value: datetime


class OrdinalFloatExpression(BaseModel):
    """Leaf node for ordinal comparisons on float sample fields."""

    type: Literal["float_field_comparison"] = "float_field_comparison"
    field: FloatField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatExpression(BaseModel):
    """Leaf node for equality comparisons on equality-only float sample fields."""

    type: Literal["equality_float_field_comparison"] = "equality_float_field_comparison"
    field: EqualityFloatField
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagsContainsExpression(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tag_contains"] = "tag_contains"
    tag_name: str


class AnnotationLabelExpression(BaseModel):
    """Criterion for equality comparisons on annotation labels."""

    type: Literal["annotation_label_comparison"] = "annotation_label_comparison"
    field: AnnotationLabelField
    operator: EqualityComparisonOperator
    value: StrictStr


class AnnotationGeometryExpression(BaseModel):
    """Criterion for ordinal comparisons on annotation geometry."""

    type: Literal["annotation_geometry_comparison"] = "annotation_geometry_comparison"
    field: AnnotationGeometryField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


ObjectDetectionCriterion = Annotated[
    Union[AnnotationLabelExpression, AnnotationGeometryExpression],
    Field(discriminator="type"),
]
InstanceSegmentationCriterion = Annotated[
    Union[AnnotationLabelExpression, AnnotationGeometryExpression],
    Field(discriminator="type"),
]


class ClassificationMatchExpression(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_annotation_query"] = "classification_annotation_query"
    criteria: list[AnnotationLabelExpression] = Field(min_length=1)


class ObjectDetectionMatchExpression(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_annotation_query"] = "object_detection_annotation_query"
    criteria: list[ObjectDetectionCriterion] = Field(min_length=1)


class InstanceSegmentationMatchExpression(BaseModel):
    """Leaf node checking if a sample has a matching instance segmentation annotation."""

    type: Literal["instance_segmentation_annotation_query"] = (
        "instance_segmentation_annotation_query"
    )
    criteria: list[InstanceSegmentationCriterion] = Field(min_length=1)


class AndExpression(BaseModel):
    """Boolean AND of multiple query nodes."""

    type: Literal["and"] = "and"
    children: list[QueryNode] = Field(min_length=1)


class OrExpression(BaseModel):
    """Boolean OR of multiple query nodes."""

    type: Literal["or"] = "or"
    children: list[QueryNode] = Field(min_length=1)


class NotExpression(BaseModel):
    """Boolean NOT of a single query node."""

    type: Literal["not"] = "not"
    child: QueryNode


QueryNode = Annotated[
    Union[
        StringExpression,
        IntegerExpression,
        DatetimeExpression,
        OrdinalFloatExpression,
        EqualityFloatExpression,
        TagsContainsExpression,
        ClassificationMatchExpression,
        ObjectDetectionMatchExpression,
        InstanceSegmentationMatchExpression,
        AndExpression,
        OrExpression,
        NotExpression,
    ],
    Field(discriminator="type"),
]

AndExpression.model_rebuild()
OrExpression.model_rebuild()
NotExpression.model_rebuild()


class QueryTree(BaseModel):
    """Top-level model representing a complete query tree."""

    root: QueryNode
