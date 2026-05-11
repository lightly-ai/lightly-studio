"""Sorting models and translation utilities."""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel

from lightly_studio.core.dataset_query.order_by import OrderByExpression
from lightly_studio.core.dataset_query.query_translation import sort_to_order_by


class SortDirection(str, Enum):
    """Sort direction for a sort field expression."""

    asc = "asc"
    desc = "desc"


class SortFieldSource(str, Enum):
    """Source of the field to sort by."""

    image = "image"
    metadata = "metadata"


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

    source: SortFieldSource
    field_name: str
    direction: SortDirection
    is_numeric: bool | None = None


def sort_field_expr_to_order_by(expr: SortFieldExpr) -> OrderByExpression:
    """Translate a SortFieldExpr to an OrderByExpression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    direction: Literal["asc", "desc"] = "asc" if expr.direction == SortDirection.asc else "desc"
    return sort_to_order_by(
        (expr.source, expr.field_name), direction, cast_to_float=bool(expr.is_numeric)
    )
