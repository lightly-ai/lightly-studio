"""Pydantic models for the query expression used in GUI-based querying."""

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


class FieldRef(BaseModel):
    """Reference to a field on a table."""

    table: str
    name: str


class StringExpr(BaseModel):
    """Leaf node for equality comparisons on string sample fields."""

    type: Literal["string_expr"] = "string_expr"
    field: FieldRef
    operator: EqualityComparisonOperator
    value: StrictStr


class IntegerExpr(BaseModel):
    """Leaf node for ordinal comparisons on integer sample fields."""

    type: Literal["integer_expr"] = "integer_expr"
    field: FieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt


class DatetimeExpr(BaseModel):
    """Leaf node for ordinal comparisons on datetime sample fields."""

    type: Literal["datetime_expr"] = "datetime_expr"
    field: FieldRef
    operator: OrdinalComparisonOperator
    value: datetime


class OrdinalFloatExpr(BaseModel):
    """Leaf node for ordinal comparisons on float sample fields."""

    type: Literal["ordinal_float_expr"] = "ordinal_float_expr"
    field: FieldRef
    operator: OrdinalComparisonOperator
    value: StrictInt | StrictFloat


class EqualityFloatExpr(BaseModel):
    """Leaf node for equality comparisons on equality-only float sample fields."""

    type: Literal["equality_float_expr"] = "equality_float_expr"
    field: FieldRef
    operator: EqualityComparisonOperator
    value: StrictInt | StrictFloat


class TagsContainsExpr(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tags_contains_expr"] = "tags_contains_expr"
    field: FieldRef
    tag_name: str


class ClassificationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_match_expr"] = "classification_match_expr"
    subexpr: MatchExpr


class ObjectDetectionMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_match_expr"] = "object_detection_match_expr"
    subexpr: MatchExpr


class InstanceSegmentationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching instance segmentation annotation."""

    type: Literal["instance_segmentation_match_expr"] = "instance_segmentation_match_expr"
    subexpr: MatchExpr


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


# Rebuild models with recursive references between them.
ClassificationMatchExpr.model_rebuild()
ObjectDetectionMatchExpr.model_rebuild()
InstanceSegmentationMatchExpr.model_rebuild()
AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()


class QueryExpr(BaseModel):
    """Top-level model representing a complete query expression."""

    match_expr: MatchExpr
