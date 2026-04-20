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


class StringFieldComparison(BaseModel):
    """Leaf node comparing a string sample field to a string value."""

    type: Literal["string_field_comparison"] = "string_field_comparison"
    field: ImageStringField | VideoStringField
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerFieldComparison(BaseModel):
    """Leaf node comparing an integer sample field to an integer value."""

    type: Literal["integer_field_comparison"] = "integer_field_comparison"
    field: ImageIntegerField | VideoIntegerField
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeFieldComparison(BaseModel):
    """Leaf node comparing a datetime sample field to a datetime value."""

    type: Literal["datetime_field_comparison"] = "datetime_field_comparison"
    field: ImageDatetimeField
    operator: OrdinalComparisonOperator
    value: datetime


class FloatFieldComparison(BaseModel):
    """Leaf node comparing a float sample field to a numeric value."""

    type: Literal["float_field_comparison"] = "float_field_comparison"
    field: VideoFloatField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatFieldComparison(BaseModel):
    """Leaf node comparing an equality-only float field to a numeric value."""

    type: Literal["equality_float_field_comparison"] = "equality_float_field_comparison"
    field: VideoEqualityFloatField
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagContains(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tag_contains"] = "tag_contains"
    tag_name: str


class AnnotationLabelComparison(BaseModel):
    """Criterion comparing an annotation label to a string value."""

    type: Literal["annotation_label_comparison"] = "annotation_label_comparison"
    field: AnnotationLabelField
    operator: EqualityComparisonOperator
    value: StrictStr


class AnnotationGeometryComparison(BaseModel):
    """Criterion comparing annotation geometry to a numeric value."""

    type: Literal["annotation_geometry_comparison"] = "annotation_geometry_comparison"
    field: AnnotationGeometryField
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


ObjectDetectionCriterion = Annotated[
    Union[AnnotationLabelComparison, AnnotationGeometryComparison],
    Field(discriminator="type"),
]
InstanceSegmentationCriterion = Annotated[
    Union[AnnotationLabelComparison, AnnotationGeometryComparison],
    Field(discriminator="type"),
]


class ClassificationAnnotationQuery(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_annotation_query"] = "classification_annotation_query"
    criteria: list[AnnotationLabelComparison] = Field(min_length=1)


class ObjectDetectionAnnotationQuery(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_annotation_query"] = "object_detection_annotation_query"
    criteria: list[ObjectDetectionCriterion] = Field(min_length=1)


class InstanceSegmentationAnnotationQuery(BaseModel):
    """Leaf node checking if a sample has a matching instance segmentation annotation."""

    type: Literal["instance_segmentation_annotation_query"] = (
        "instance_segmentation_annotation_query"
    )
    criteria: list[InstanceSegmentationCriterion] = Field(min_length=1)


class AndNode(BaseModel):
    """Boolean AND of multiple query nodes."""

    type: Literal["and"] = "and"
    children: list[QueryNode] = Field(min_length=1)


class OrNode(BaseModel):
    """Boolean OR of multiple query nodes."""

    type: Literal["or"] = "or"
    children: list[QueryNode] = Field(min_length=1)


class NotNode(BaseModel):
    """Boolean NOT of a single query node."""

    type: Literal["not"] = "not"
    child: QueryNode


QueryNode = Annotated[
    Union[
        StringFieldComparison,
        IntegerFieldComparison,
        DatetimeFieldComparison,
        FloatFieldComparison,
        EqualityFloatFieldComparison,
        TagContains,
        ClassificationAnnotationQuery,
        ObjectDetectionAnnotationQuery,
        InstanceSegmentationAnnotationQuery,
        AndNode,
        OrNode,
        NotNode,
    ],
    Field(discriminator="type"),
]

AndNode.model_rebuild()
OrNode.model_rebuild()
NotNode.model_rebuild()


class QueryTree(BaseModel):
    """Top-level model representing a complete query tree."""

    root: QueryNode
