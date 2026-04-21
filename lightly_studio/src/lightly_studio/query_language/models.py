"""Pydantic models for the query tree used in GUI-based querying."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Union

from pydantic import BaseModel, Field, StrictFloat, StrictInt, StrictStr
from typing_extensions import Literal, TypeAlias


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


class StringFieldRef(BaseModel):
    """Reference to a string field."""

    table: str
    name: str


class IntegerFieldRef(BaseModel):
    """Reference to an integer field."""

    table: str
    name: str


class DatetimeFieldRef(BaseModel):
    """Reference to a datetime field."""

    table: str
    name: str


class OrdinalFloatFieldRef(BaseModel):
    """Reference to a float field with ordinal comparisons."""

    table: str
    name: str


class EqualityFloatFieldRef(BaseModel):
    """Reference to a float field with equality-only comparisons."""

    table: str
    name: str


class TagsFieldRef(BaseModel):
    """Reference to the tags relationship."""

    table: str
    name: str


class AnnotationLabelFieldRef(BaseModel):
    """Reference to a label field on an annotation table."""

    table: str
    name: str


class AnnotationGeometryFieldRef(BaseModel):
    """Reference to a geometry field on an annotation table."""

    table: str
    name: str


class StringExpr(BaseModel):
    """Leaf node for equality comparisons on string sample fields."""

    type: Literal["string_expr"] = "string_expr"
    field: StringFieldRef
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerExpr(BaseModel):
    """Leaf node for ordinal comparisons on integer sample fields."""

    type: Literal["integer_expr"] = "integer_expr"
    field: IntegerFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeExpr(BaseModel):
    """Leaf node for ordinal comparisons on datetime sample fields."""

    type: Literal["datetime_expr"] = "datetime_expr"
    field: DatetimeFieldRef
    operator: OrdinalComparisonOperator
    value: datetime


class OrdinalFloatExpr(BaseModel):
    """Leaf node for ordinal comparisons on float sample fields."""

    type: Literal["ordinal_float_expr"] = "ordinal_float_expr"
    field: OrdinalFloatFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatExpr(BaseModel):
    """Leaf node for equality comparisons on equality-only float sample fields."""

    type: Literal["equality_float_expr"] = "equality_float_expr"
    field: EqualityFloatFieldRef
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagsContainsExpr(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tags_contains_expr"] = "tags_contains_expr"
    field: TagsFieldRef
    tag_name: str


class AnnotationLabelExpr(BaseModel):
    """Criterion for equality comparisons on annotation labels."""

    type: Literal["annotation_label_expr"] = "annotation_label_expr"
    field: AnnotationLabelFieldRef
    operator: EqualityComparisonOperator
    value: StrictStr


class AnnotationGeometryExpr(BaseModel):
    """Criterion for ordinal comparisons on annotation geometry."""

    type: Literal["annotation_geometry_expr"] = "annotation_geometry_expr"
    field: AnnotationGeometryFieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


ObjectDetectionExpr: TypeAlias = Annotated[
    Union[AnnotationLabelExpr, AnnotationGeometryExpr],
    Field(discriminator="type"),
]
InstanceSegmentationExpr: TypeAlias = Annotated[
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


MatchExpr: TypeAlias = Annotated[
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
