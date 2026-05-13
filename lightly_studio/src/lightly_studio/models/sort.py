"""Sorting models and translation utilities."""

from __future__ import annotations

from enum import Enum
from uuid import UUID

from pydantic import BaseModel

from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField, OrderByMetric
from lightly_studio.core.dataset_query.query_translation import sort_to_order_by
from lightly_studio.models.sort_direction import SortDirection


class SortFieldSource(str, Enum):
    """Source of the field to sort by."""

    image = "image"
    metric = "metric"


class SortFieldExpr(BaseModel):
    """A sorting expression for a single field.

    Attributes:
        source: The source of the field (e.g., "image" or "metric").
        field_name: The field to sort by.
        direction: The sort direction, either ascending or descending.
        evaluation_run_id: Required when source is "metric".
    """

    source: SortFieldSource
    field_name: str
    direction: SortDirection
    evaluation_run_id: UUID | None = None


def sort_field_expr_to_order_by(expr: SortFieldExpr) -> OrderByExpression:
    """Translate a SortFieldExpr to an OrderByExpression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    if expr.source == SortFieldSource.metric:
        if expr.evaluation_run_id is None:
            raise ValueError("evaluation_run_id is required for metric sort")
        order = OrderByMetric(
            evaluation_run_id=expr.evaluation_run_id,
            metric_name=expr.field_name,
        )
        if expr.direction == SortDirection.desc:
            order.desc()
        return order
    return sort_to_order_by((expr.source, expr.field_name), expr.direction)
