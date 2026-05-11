"""Tests for sort models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lightly_studio.errors import QueryExprError
from lightly_studio.models.sort import (
    SortDirection,
    SortFieldExpr,
    SortFieldSource,
    sort_field_expr_to_order_by,
)

_IMAGE_SORT_FIELD_NAMES = ["file_name", "file_path_abs", "created_at", "width", "height"]

def test_sort_field_expr__valid_directions() -> None:
    expr_asc = SortFieldExpr(
        source=SortFieldSource.image, field_name="file_name", direction=SortDirection.asc
    )
    expr_desc = SortFieldExpr(
        source=SortFieldSource.image, field_name="file_name", direction=SortDirection.desc
    )

    assert expr_asc.direction == SortDirection.asc
    assert expr_desc.direction == SortDirection.desc


def test_sort_field_expr__rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        SortFieldExpr.model_validate(
            {
                "source": "image",
                "field_name": "file_name",
                "direction": "invalid_direction",
            }
        )


def test_sort_field_expr_to_order_by__rejects_unknown_field() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image, field_name="invalid_field", direction=SortDirection.asc
    )
    with pytest.raises(QueryExprError):
        sort_field_expr_to_order_by(expr)


def test_sort_field_expr_to_order_by__ascending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image, field_name="file_name", direction=SortDirection.asc
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is True


def test_sort_field_expr_to_order_by__descending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image, field_name="width", direction=SortDirection.desc
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is False


def test_sort_field_expr_to_order_by__all_fields_map() -> None:
    for field_name in _IMAGE_SORT_FIELD_NAMES:
        expr = SortFieldExpr(
            source=SortFieldSource.image, field_name=field_name, direction=SortDirection.asc
        )
        order_by = sort_field_expr_to_order_by(expr)
        assert order_by is not None
