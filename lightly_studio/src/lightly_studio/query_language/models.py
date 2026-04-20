"""Pydantic models for the query tree used in GUI-based querying."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class ComparisonOperator(str, Enum):
    """Comparison operators for field comparisons."""

    EQ = "=="
    NEQ = "!="
    LT = "<"
    GT = ">"
    LTE = "<="
    GTE = ">="


class SampleField(str, Enum):
    """Fields available for querying sample properties.

    Union of image and video fields. The translation layer validates
    field/sample-type compatibility.
    """

    FILE_NAME = "file_name"
    WIDTH = "width"
    HEIGHT = "height"
    FILE_PATH_ABS = "file_path_abs"
    CREATED_AT = "created_at"
    DURATION_S = "duration_s"
    FPS = "fps"


class AnnotationField(str, Enum):
    """Fields available for querying annotation properties.

    Union of all annotation type fields. The translation layer validates
    field/annotation-type compatibility.
    """

    LABEL = "label"
    X = "x"
    Y = "y"
    WIDTH = "width"
    HEIGHT = "height"


class AnnotationQueryType(str, Enum):
    """Annotation types for annotation queries.

    Redefined (not imported from models/annotation/) to keep query models DB-independent.
    """

    CLASSIFICATION = "classification"
    OBJECT_DETECTION = "object_detection"
    INSTANCE_SEGMENTATION = "instance_segmentation"


class FieldComparison(BaseModel):
    """Leaf node comparing a sample field to a value."""

    type: Literal["field_comparison"] = "field_comparison"
    field: SampleField
    operator: ComparisonOperator
    value: str | int | float | datetime


class TagContains(BaseModel):
    """Leaf node checking if a sample has a specific tag."""

    type: Literal["tag_contains"] = "tag_contains"
    tag_name: str


class AnnotationFieldComparison(BaseModel):
    """Comparison of an annotation field to a value.

    Not part of the QueryNode union — used only inside AnnotationQuery.criteria.
    """

    field: AnnotationField
    operator: ComparisonOperator
    value: str | int | float


class AnnotationQuery(BaseModel):
    """Leaf node checking if a sample has an annotation matching criteria."""

    type: Literal["annotation_query"] = "annotation_query"
    annotation_type: AnnotationQueryType
    criteria: list[AnnotationFieldComparison] = Field(min_length=1)


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
    Union[FieldComparison, TagContains, AnnotationQuery, AndNode, OrNode, NotNode],
    Field(discriminator="type"),
]

AndNode.model_rebuild()
OrNode.model_rebuild()
NotNode.model_rebuild()


class QueryTree(BaseModel):
    """Top-level model representing a complete query tree."""

    root: QueryNode
