"""Sorting models and translation utilities."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from lightly_studio.core.dataset_query.order_by import OrderByField
from lightly_studio.core.dataset_query.query_translation import sort_to_order_by
from lightly_studio.models.sort_direction import SortDirection


class SortFieldSource(str, Enum):
    """Source of the field to sort by."""

    image = "image"


class SortFieldExpr(BaseModel):
    """A sorting expression for a single field.

    Attributes:
        source: The source of the field (e.g., "image").
        field_name: The field to sort by.
        direction: The sort direction, either ascending or descending.
    """

    source: SortFieldSource
    field_name: str
    direction: SortDirection


def sort_field_expr_to_order_by(expr: SortFieldExpr) -> OrderByField:
    """Translate a SortFieldExpr to an OrderByField expression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByField ready to be applied to a database query.
    """
    return sort_to_order_by((expr.source, expr.field_name), expr.direction)
