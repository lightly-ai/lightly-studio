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
    video = "video"
    metadata = "metadata"
    evaluation_metric = "evaluation_metric"


class SortFieldExprBase(BaseModel):
    """Fields shared by every single-field sorting expression.

    Subclasses narrow ``source`` to the sources their endpoint can reach. A sample
    table only appears in the FROM clause of queries over that sample type, so a
    field from the wrong source would be cross-joined instead of rejected.

    Attributes:
        source: The source of the field (e.g., "image", "video" or "metadata").
        field_name: The field to sort by.
        direction: The sort direction, either ascending or descending.
    """

    source: SortFieldSource
    field_name: str
    direction: SortDirection


class ImageSortFieldExpr(SortFieldExprBase):
    """A sorting expression for a single field of an image."""

    source: Literal[SortFieldSource.image, SortFieldSource.metadata]


class VideoSortFieldExpr(SortFieldExprBase):
    """A sorting expression for a single field of a video.

    Evaluation metrics are image-only, so they have no counterpart here.
    """

    source: Literal[SortFieldSource.video, SortFieldSource.metadata]


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


ImageSortExpr = Annotated[
    Union[ImageSortFieldExpr, EvaluationMetricSortExpr],
    Field(discriminator="source"),
]


def sort_field_expr_to_order_by(expr: SortFieldExprBase) -> OrderByExpression:
    """Translate a single-field sort expression to an OrderByExpression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    return sort_to_order_by(
        key=(expr.source, expr.field_name),
        direction=expr.direction,
    )


def image_sort_expr_to_order_by(expr: ImageSortExpr) -> OrderByExpression:
    """Translate an ImageSortExpr (image, metadata, or evaluation metric) to an OrderByExpression.

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
