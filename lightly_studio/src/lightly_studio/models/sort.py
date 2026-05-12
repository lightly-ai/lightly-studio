"""Sorting models and translation utilities."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field

from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.core.dataset_query.query_translation import (
    evaluation_metric_sort_to_order_by,
    sort_to_order_by,
)
from lightly_studio.models.sort_direction import SortDirection


class SortFieldSource(str, Enum):
    """Source of the field to sort by."""

    image = "image"
    metadata = "metadata"
    evaluation_metric = "evaluation_metric"


class SortFieldExpr(BaseModel):
    """A sorting expression for a single field.

    Attributes:
        source: The source of the field (e.g., "image" or "metadata").
        field_name: The field to sort by.
        direction: The sort direction, either ascending or descending.
        is_numeric: Whether the field holds numeric values.  When ``True``,
            the extracted value is cast to float for correct numeric ordering.
            Only relevant when ``source`` is ``"metadata"``.
    """

    source: Literal[SortFieldSource.image, SortFieldSource.metadata]
    field_name: str
    direction: SortDirection
    is_numeric: bool | None = None


class EvaluationMetricSortExpr(BaseModel):
    """A sorting expression for an evaluation metric field.

    Attributes:
        source: Always ``"evaluation_metric"`` (discriminator for the union type).
        evaluation_run_name: The name of the evaluation run to sort by.
        metric_name: The metric name to sort by.
        direction: The sort direction, either ascending or descending.
    """

    source: Literal[SortFieldSource.evaluation_metric] = SortFieldSource.evaluation_metric
    evaluation_run_name: str
    metric_name: str
    direction: SortDirection


SortExpr = Annotated[
    Union[SortFieldExpr, EvaluationMetricSortExpr],
    Field(discriminator="source"),
]


def sort_field_expr_to_order_by(expr: SortFieldExpr) -> OrderByExpression:
    """Translate a SortFieldExpr to an OrderByExpression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    return sort_to_order_by(
        key=(expr.source, expr.field_name),
        direction=expr.direction,
        cast_to_float=bool(expr.is_numeric),
    )


def sort_expr_to_order_by(expr: SortExpr) -> OrderByExpression:
    """Translate a SortExpr (image, metadata, or evaluation metric) to an OrderByExpression.

    Args:
        expr: The sort expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    if isinstance(expr, EvaluationMetricSortExpr):
        return evaluation_metric_sort_to_order_by(
            evaluation_run_name=expr.evaluation_run_name,
            metric_name=expr.metric_name,
            direction=expr.direction,
        )
    return sort_field_expr_to_order_by(expr)
