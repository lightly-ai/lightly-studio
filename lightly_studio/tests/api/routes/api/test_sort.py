"""Tests for sort models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from lightly_studio.api.routes.api.sort import (
    ImageSortField,
    SortDirection,
    SortFieldExpr,
    sort_field_expr_to_order_by,
)


def test_sort_field_expr__valid_fields() -> None:
    for field in ImageSortField:
        expr = SortFieldExpr(field_name=field, direction=SortDirection.asc)
        assert expr.field_name == field


def test_sort_field_expr__valid_directions() -> None:
    expr_asc = SortFieldExpr(field_name=ImageSortField.file_name, direction=SortDirection.asc)
    expr_desc = SortFieldExpr(field_name=ImageSortField.file_name, direction=SortDirection.desc)

    assert expr_asc.direction == SortDirection.asc
    assert expr_desc.direction == SortDirection.desc


def test_sort_field_expr__rejects_invalid_field() -> None:
    with pytest.raises(ValidationError):
        SortFieldExpr.model_validate(
            {"field_name": "invalid_field", "direction": SortDirection.asc}
        )


def test_sort_field_expr__rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        SortFieldExpr.model_validate(
            {"field_name": ImageSortField.file_name, "direction": "invalid_direction"}
        )


def test_sort_field_expr_to_order_by__ascending() -> None:
    expr = SortFieldExpr(field_name=ImageSortField.file_name, direction=SortDirection.asc)
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is True


def test_sort_field_expr_to_order_by__descending() -> None:
    expr = SortFieldExpr(field_name=ImageSortField.width, direction=SortDirection.desc)
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is False


def test_sort_field_expr_to_order_by__all_fields_map() -> None:
    for field in ImageSortField:
        expr = SortFieldExpr(field_name=field, direction=SortDirection.asc)
        order_by = sort_field_expr_to_order_by(expr)
        assert order_by is not None
