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


class StringExpr(BaseModel):
    """Leaf node for equality comparisons on string sample fields."""

    type: Literal["string_expr"] = "string_expr"
    field: StringField
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerExpr(BaseModel):
    """Leaf node for ordinal comparisons on integer sample fields."""

    type: Literal["integer_expr"] = "integer_expr"
    field: IntegerField
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeExpr(BaseModel):
    """Leaf node for ordinal comparisons on datetime sample fields."""

    type: Literal["datetime_expr"] = "datetime_expr"
    field: DatetimeField
    operator: OrdinalComparisonOperator
    value: datetime


class OrdinalFloatExpr(BaseModel):
    """Leaf node for ordinal comparisons on float sample fields."""

    type: Literal["ordinal_float_expr"] = "ordinal_float_expr"
    field: FloatField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatExpr(BaseModel):
    """Leaf node for equality comparisons on equality-only float sample fields."""

    type: Literal["equality_float_expr"] = "equality_float_expr"
    field: EqualityFloatField
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagsContainsExpr(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tags_contains_expr"] = "tags_contains_expr"
    tag_name: str


class AnnotationLabelExpr(BaseModel):
    """Criterion for equality comparisons on annotation labels."""

    type: Literal["annotation_label_expr"] = "annotation_label_expr"
    field: AnnotationLabelField
    operator: EqualityComparisonOperator
    value: StrictStr


class AnnotationGeometryExpr(BaseModel):
    """Criterion for ordinal comparisons on annotation geometry."""

    type: Literal["annotation_geometry_expr"] = "annotation_geometry_expr"
    field: AnnotationGeometryField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


ObjectDetectionExpr = Annotated[
    Union[AnnotationLabelExpr, AnnotationGeometryExpr],
    Field(discriminator="type"),
]
InstanceSegmentationExpr = Annotated[
    Union[AnnotationLabelExpr, AnnotationGeometryExpr],
    Field(discriminator="type"),
]


class ClassificationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_match_expr"] = "classification_match_expr"
    criteria: list[AnnotationLabelExpr] = Field(min_length=1)


class ObjectDetectionMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_match_expr"] = "object_detection_match_expr"
    criteria: list[ObjectDetectionExpr] = Field(min_length=1)


class InstanceSegmentationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching instance segmentation annotation."""

    type: Literal["instance_segmentation_match_expr"] = "instance_segmentation_match_expr"
    criteria: list[InstanceSegmentationExpr] = Field(min_length=1)


class AndExpr(BaseModel):
    """Boolean AND of multiple query nodes."""

    type: Literal["and"] = "and"
    children: list[MatchExpr] = Field(min_length=1)


class OrExpr(BaseModel):
    """Boolean OR of multiple query nodes."""

    type: Literal["or"] = "or"
    children: list[MatchExpr] = Field(min_length=1)


class NotExpr(BaseModel):
    """Boolean NOT of a single query node."""

    type: Literal["not"] = "not"
    child: MatchExpr


MatchExpr = Annotated[
    Union[
        StringExpr,
        IntegerExpr,
        DatetimeExpr,
        OrdinalFloatExpr,
        EqualityFloatExpr,
        TagsContainsExpr,
        ClassificationMatchExpr,
        ObjectDetectionMatchExpr,
        InstanceSegmentationMatchExpr,
        AndExpr,
        OrExpr,
        NotExpr,
    ],
    Field(discriminator="type"),
]

AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()


class QueryTree(BaseModel):
    """Top-level model representing a complete query tree."""

    root: MatchExpr
