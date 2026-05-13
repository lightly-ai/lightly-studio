"""Tests for sort models."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByMetadataField,
)
from lightly_studio.errors import QueryExprError
from lightly_studio.models.sort import (
    EvaluationMetricSortExpr,
    SortExpr,
    SortFieldExpr,
    SortFieldSource,
    sort_expr_to_order_by,
    sort_field_expr_to_order_by,
)
from lightly_studio.models.sort_direction import SortDirection

_IMAGE_SORT_FIELD_NAMES = ["file_name", "file_path_abs", "created_at", "width", "height"]


def test_sort_field_expr__valid_directions() -> None:
    expr_asc = SortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.asc,
        is_numeric=False,
    )
    expr_desc = SortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.desc,
        is_numeric=False,
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
                "is_numeric": False,
            }
        )


def test_sort_field_expr_to_order_by__rejects_unknown_field() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image,
        field_name="invalid_field",
        direction=SortDirection.asc,
        is_numeric=False,
    )
    with pytest.raises(QueryExprError):
        sort_field_expr_to_order_by(expr)


def test_sort_field_expr_to_order_by__ascending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.asc,
        is_numeric=False,
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is True


def test_sort_field_expr_to_order_by__descending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.image,
        field_name="width",
        direction=SortDirection.desc,
        is_numeric=False,
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert order_by.ascending is False


def test_sort_field_expr_to_order_by__all_fields_map() -> None:
    for field_name in _IMAGE_SORT_FIELD_NAMES:
        expr = SortFieldExpr(
            source=SortFieldSource.image,
            field_name=field_name,
            direction=SortDirection.asc,
            is_numeric=False,
        )
        order_by = sort_field_expr_to_order_by(expr)
        assert order_by is not None


def test_sort_field_expr_to_order_by__metadata_ascending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="brightness",
        direction=SortDirection.asc,
        is_numeric=False,
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "brightness"
    assert order_by.ascending is True
    assert order_by.cast_to_float is False


def test_sort_field_expr_to_order_by__metadata_descending() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="score",
        direction=SortDirection.desc,
        is_numeric=False,
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "score"
    assert order_by.ascending is False
    assert order_by.cast_to_float is False


def test_sort_field_expr_to_order_by__metadata_arbitrary_field() -> None:
    expr = SortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="custom_metric",
        direction=SortDirection.asc,
        is_numeric=False,
    )
    order_by = sort_field_expr_to_order_by(expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "custom_metric"


def test_sort_expr_to_order_by__evaluation_metric_ascending() -> None:
    expr = EvaluationMetricSortExpr(
        evaluation_run_name="run1",
        metric_name="score",
        direction=SortDirection.asc,
    )
    order_by = sort_expr_to_order_by(expr)
    assert isinstance(order_by, OrderByEvaluationMetricField)
    assert order_by.evaluation_run_name == "run1"
    assert order_by.metric_name == "score"
    assert order_by.ascending is True


def test_sort_expr_to_order_by__evaluation_metric_descending() -> None:
    expr = EvaluationMetricSortExpr(
        evaluation_run_name="run1",
        metric_name="precision",
        direction=SortDirection.desc,
    )
    order_by = sort_expr_to_order_by(expr)
    assert isinstance(order_by, OrderByEvaluationMetricField)
    assert order_by.evaluation_run_name == "run1"
    assert order_by.metric_name == "precision"
    assert order_by.ascending is False


def test_sort_expr_discriminated_union__routes_to_evaluation_metric() -> None:
    adapter: TypeAdapter[SortExpr] = TypeAdapter(SortExpr)
    expr = adapter.validate_python(
        {
            "source": "evaluation_metric",
            "evaluation_run_name": "run1",
            "metric_name": "score",
            "direction": "asc",
        }
    )
    assert isinstance(expr, EvaluationMetricSortExpr)
    assert expr.evaluation_run_name == "run1"
    assert expr.metric_name == "score"


def test_sort_expr_discriminated_union__routes_to_sort_field_expr() -> None:
    adapter: TypeAdapter[SortExpr] = TypeAdapter(SortExpr)
    expr = adapter.validate_python(
        {
            "source": "image",
            "field_name": "file_name",
            "direction": "asc",
        }
    )
    assert isinstance(expr, SortFieldExpr)
    assert expr.field_name == "file_name"
