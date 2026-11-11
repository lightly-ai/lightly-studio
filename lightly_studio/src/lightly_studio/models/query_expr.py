"""Pydantic models for the query expression used in GUI-based querying."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, TypeAlias, Union

import pydantic
from pydantic import BaseModel, Field, StrictBool, StrictFloat, StrictInt, StrictStr
from pydantic_core import PydanticCustomError
from typing_extensions import Self


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
    tag_name: StrictStr


class MetadataComparisonExpr(BaseModel):
    """Compare a sample's metadata at a dot-separated path with optional array indices.

    Attributes:
        path: Metadata path, such as ``odometry.acc[1]``.
        operator: Equality, inequality, or numeric ordering operator.
        value: Strict JSON scalar. Ordering requires a number, excluding booleans.
    """

    type: Literal["metadata_comparison_expr"] = "metadata_comparison_expr"
    path: str
    operator: OrdinalComparisonOperator
    value: StrictStr | StrictBool | StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]

    @pydantic.model_validator(mode="after")
    def validate_comparison(self) -> Self:  # noqa: N804
        """Reject ordering comparisons with strings or booleans."""
        if self.operator not in (OrdinalComparisonOperator.EQ, OrdinalComparisonOperator.NEQ) and (
            isinstance(self.value, (str, bool))
        ):
            raise PydanticCustomError(
                "metadata_ordering", "Metadata ordering comparisons require a number."
            )
        return self


class EvaluationMetricComparisonExpr(BaseModel):
    """Compare a persisted metric within a sample or annotation evaluation.

    Attributes:
        metric_name: Persisted metric name, including custom metric names.
        operator: Numeric comparison operator.
        value: Finite numeric threshold; strings and booleans are rejected.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["evaluation_metric_comparison_expr"] = "evaluation_metric_comparison_expr"
    metric_name: StrictStr
    operator: OrdinalComparisonOperator
    value: StrictInt | Annotated[StrictFloat, Field(allow_inf_nan=False)]


class EvaluationMetricAndExpr(BaseModel):
    """Require every child metric predicate to match within one sample evaluation."""

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["and"] = "and"
    children: list[SampleEvaluationMetricExpr] = Field(min_length=1)


class EvaluationMetricOrExpr(BaseModel):
    """Require at least one child metric predicate within one sample evaluation."""

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["or"] = "or"
    children: list[SampleEvaluationMetricExpr] = Field(min_length=1)


class EvaluationMetricNotExpr(BaseModel):
    """Negate a metric predicate within one sample evaluation."""

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["not"] = "not"
    child: SampleEvaluationMetricExpr


SampleEvaluationMetricExpr: TypeAlias = Annotated[
    Union[
        EvaluationMetricComparisonExpr,
        EvaluationMetricAndExpr,
        EvaluationMetricOrExpr,
        EvaluationMetricNotExpr,
    ],
    Field(discriminator="type"),
]


class SampleEvaluationMatchExpr(BaseModel):
    """Match evaluated samples in a named run using ANDed metric criteria.

    An empty criteria list matches all samples evaluated by the run. Each criterion
    can combine metric comparisons with AND, OR, and NOT.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["sample_evaluation_match_expr"] = "sample_evaluation_match_expr"
    run_name: StrictStr
    criteria: list[SampleEvaluationMetricExpr] = Field(default_factory=list)


class ConfusionMatchExpr(BaseModel):
    """Match a confusion cell in a named run.

    All metric criteria must match the same ground-truth/prediction annotation pair.
    Equal class names select the corresponding diagonal cell.
    """

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["confusion_match_expr"] = "confusion_match_expr"
    run_name: StrictStr
    ground_truth: StrictStr
    prediction: StrictStr
    criteria: list[EvaluationMetricComparisonExpr] = Field(default_factory=list)


class FalsePositiveMatchExpr(BaseModel):
    """Match an unmatched prediction of the selected class in a named run."""

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["false_positive_match_expr"] = "false_positive_match_expr"
    run_name: StrictStr
    prediction: StrictStr


class FalseNegativeMatchExpr(BaseModel):
    """Match an unmatched ground-truth annotation of the selected class in a named run."""

    model_config = pydantic.ConfigDict(extra="forbid")

    type: Literal["false_negative_match_expr"] = "false_negative_match_expr"
    run_name: StrictStr
    ground_truth: StrictStr


class ClassificationMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching classification annotation."""

    type: Literal["classification_match_expr"] = "classification_match_expr"
    subexpr: MatchExpr


class ObjectDetectionMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching object detection annotation."""

    type: Literal["object_detection_match_expr"] = "object_detection_match_expr"
    subexpr: MatchExpr


class SegmentationMaskMatchExpr(BaseModel):
    """Leaf node checking if a sample has a matching segmentation mask annotation."""

    type: Literal["segmentation_mask_match_expr"] = "segmentation_mask_match_expr"
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
        MetadataComparisonExpr,
        SampleEvaluationMatchExpr,
        ConfusionMatchExpr,
        FalsePositiveMatchExpr,
        FalseNegativeMatchExpr,
        ClassificationMatchExpr,
        ObjectDetectionMatchExpr,
        SegmentationMaskMatchExpr,
        AndExpr,
        OrExpr,
        NotExpr,
    ],
    Field(discriminator="type"),
]


# Rebuild models with recursive references between them.
EvaluationMetricAndExpr.model_rebuild()
EvaluationMetricOrExpr.model_rebuild()
EvaluationMetricNotExpr.model_rebuild()
SampleEvaluationMatchExpr.model_rebuild()
ClassificationMatchExpr.model_rebuild()
ObjectDetectionMatchExpr.model_rebuild()
SegmentationMaskMatchExpr.model_rebuild()
AndExpr.model_rebuild()
OrExpr.model_rebuild()
NotExpr.model_rebuild()


class QueryExpr(BaseModel):
    """Top-level model representing a complete query expression."""

    match_expr: MatchExpr

    @pydantic.model_validator(mode="after")
    def validate_evaluation_scope(self) -> Self:  # noqa: N804
        """Evaluation filters apply to samples, not nested annotation queries."""
        _validate_evaluation_scope(expr=self.match_expr, in_annotation=False)
        return self


def _validate_evaluation_scope(expr: MatchExpr, in_annotation: bool) -> None:
    if isinstance(
        expr,
        (
            SampleEvaluationMatchExpr,
            ConfusionMatchExpr,
            FalsePositiveMatchExpr,
            FalseNegativeMatchExpr,
        ),
    ):
        if in_annotation:
            raise ValueError("Evaluation filters cannot be nested inside annotation queries.")
    elif isinstance(
        expr, (ClassificationMatchExpr, ObjectDetectionMatchExpr, SegmentationMaskMatchExpr)
    ):
        _validate_evaluation_scope(expr=expr.subexpr, in_annotation=True)
    elif isinstance(expr, (AndExpr, OrExpr)):
        for child in expr.children:
            _validate_evaluation_scope(expr=child, in_annotation=in_annotation)
    elif isinstance(expr, NotExpr):
        _validate_evaluation_scope(expr=expr.child, in_annotation=in_annotation)
