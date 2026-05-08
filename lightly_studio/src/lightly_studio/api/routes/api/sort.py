"""Sorting models and translation utilities for API requests."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import OrderByField


class SortDirection(str, Enum):
    """Sort direction for a sort field expression."""

    asc = "asc"
    desc = "desc"


class ImageSortField(str, Enum):
    """Native image fields available for sorting."""

    file_name = "file_name"
    file_path_abs = "file_path_abs"
    created_at = "created_at"
    width = "width"
    height = "height"


class SortFieldExpr(BaseModel):
    """A sorting expression for a single field.

    Attributes:
        field_name: The native image field to sort by.
        direction: The sort direction, either ascending or descending.
    """

    field_name: ImageSortField
    direction: SortDirection


_IMAGE_SORT_FIELDS = {
    ImageSortField.file_name: ImageSampleField.file_name,
    ImageSortField.file_path_abs: ImageSampleField.file_path_abs,
    ImageSortField.created_at: ImageSampleField.created_at,
    ImageSortField.width: ImageSampleField.width,
    ImageSortField.height: ImageSampleField.height,
}


def sort_field_expr_to_order_by(expr: SortFieldExpr) -> OrderByField:
    """Translate a SortFieldExpr to an OrderByField expression.

    Args:
        expr: The sort field expression from the API request.

    Returns:
        An OrderByField ready to be applied to a database query.
    """
    order_by = OrderByField(_IMAGE_SORT_FIELDS[expr.field_name])
    if expr.direction == SortDirection.desc:
        order_by.desc()
    return order_by
