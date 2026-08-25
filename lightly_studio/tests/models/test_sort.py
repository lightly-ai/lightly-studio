"""Tests for sort models."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.errors import QueryExprError
from lightly_studio.models.sort import (
    EvaluationMetricSortExpr,
    ImageSortExpr,
    ImageSortFieldExpr,
    SortFieldSource,
    VideoSortFieldExpr,
    image_sort_expr_to_order_by,
    sort_field_expr_to_order_by,
)
from lightly_studio.models.sort_direction import SortDirection

_IMAGE_SORT_FIELD_TO_COLUMN = {
    "file_name": ImageSampleField.file_name,
    "file_path_abs": ImageSampleField.file_path_abs,
    "created_at": ImageSampleField.created_at,
    "width": ImageSampleField.width,
    "height": ImageSampleField.height,
}
_VIDEO_SORT_FIELD_TO_COLUMN = {
    "file_name": VideoSampleField.file_name,
    "file_path_abs": VideoSampleField.file_path_abs,
    "created_at": VideoSampleField.created_at,
    "width": VideoSampleField.width,
    "height": VideoSampleField.height,
    "duration_s": VideoSampleField.duration_s,
    "fps": VideoSampleField.fps,
}


def test_image_sort_field_expr__valid_directions() -> None:
    expr_asc = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.asc,
    )
    expr_desc = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.desc,
    )

    assert expr_asc.direction == SortDirection.asc
    assert expr_desc.direction == SortDirection.desc


def test_image_sort_field_expr__rejects_invalid_direction() -> None:
    with pytest.raises(ValidationError):
        ImageSortFieldExpr.model_validate(
            {
                "source": "image",
                "field_name": "file_name",
                "direction": "invalid_direction",
            }
        )


def test_sort_field_expr_to_order_by__image_rejects_unknown_field() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="invalid_field",
        direction=SortDirection.asc,
    )
    with pytest.raises(QueryExprError):
        sort_field_expr_to_order_by(expr=expr)


def test_sort_field_expr_to_order_by__image_ascending() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="file_name",
        direction=SortDirection.asc,
    )
    order_by = sort_field_expr_to_order_by(expr=expr)
    assert order_by.ascending is True


def test_sort_field_expr_to_order_by__image_descending() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="width",
        direction=SortDirection.desc,
    )
    order_by = sort_field_expr_to_order_by(expr=expr)
    assert order_by.ascending is False


def test_sort_field_expr_to_order_by__image_all_fields_map() -> None:
    for field_name, expected_field in _IMAGE_SORT_FIELD_TO_COLUMN.items():
        expr = ImageSortFieldExpr(
            source=SortFieldSource.image,
            field_name=field_name,
            direction=SortDirection.asc,
        )
        order_by = sort_field_expr_to_order_by(expr=expr)
        assert isinstance(order_by, OrderByField)
        assert order_by.field is expected_field


def test_sort_field_expr_to_order_by__image_field_name_not_shared_with_video() -> None:
    # `duration_s` exists on videos only; the source must select the right registry.
    expr = ImageSortFieldExpr(
        source=SortFieldSource.image,
        field_name="duration_s",
        direction=SortDirection.asc,
    )
    with pytest.raises(QueryExprError):
        sort_field_expr_to_order_by(expr=expr)


def test_image_sort_field_expr__rejects_video_source() -> None:
    # Image queries do not have `VideoTable` in the FROM clause, so a video field
    # would be cross-joined rather than sorted by.
    with pytest.raises(ValidationError):
        ImageSortFieldExpr.model_validate(
            {"source": "video", "field_name": "fps", "direction": "asc"}
        )


def test_sort_field_expr_to_order_by__video_all_fields_map() -> None:
    for field_name, expected_field in _VIDEO_SORT_FIELD_TO_COLUMN.items():
        expr = VideoSortFieldExpr(
            source=SortFieldSource.video,
            field_name=field_name,
            direction=SortDirection.asc,
        )
        order_by = sort_field_expr_to_order_by(expr=expr)
        assert isinstance(order_by, OrderByField)
        assert order_by.field is expected_field


def test_sort_field_expr_to_order_by__video_metadata_source() -> None:
    expr = VideoSortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="blur_score",
        direction=SortDirection.asc,
    )
    assert isinstance(sort_field_expr_to_order_by(expr=expr), OrderByMetadataField)


def test_sort_field_expr_to_order_by__video_rejects_unknown_field() -> None:
    expr = VideoSortFieldExpr(
        source=SortFieldSource.video,
        field_name="invalid_field",
        direction=SortDirection.asc,
    )
    with pytest.raises(QueryExprError):
        sort_field_expr_to_order_by(expr=expr)


def test_video_sort_field_expr__rejects_image_source() -> None:
    with pytest.raises(ValidationError):
        VideoSortFieldExpr.model_validate(
            {"source": "image", "field_name": "width", "direction": "asc"}
        )


def test_video_sort_field_expr__rejects_evaluation_metric_source() -> None:
    # Evaluation metrics are image-only.
    with pytest.raises(ValidationError):
        VideoSortFieldExpr.model_validate(
            {"source": "evaluation_metric", "field_name": "iou", "direction": "asc"}
        )


def test_sort_field_expr_to_order_by__image_metadata_ascending() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="brightness",
        direction=SortDirection.asc,
    )
    order_by = sort_field_expr_to_order_by(expr=expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "brightness"
    assert order_by.ascending is True


def test_sort_field_expr_to_order_by__image_metadata_descending() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="score",
        direction=SortDirection.desc,
    )
    order_by = sort_field_expr_to_order_by(expr=expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "score"
    assert order_by.ascending is False


def test_sort_field_expr_to_order_by__image_metadata_arbitrary_field() -> None:
    expr = ImageSortFieldExpr(
        source=SortFieldSource.metadata,
        field_name="custom_metric",
        direction=SortDirection.asc,
    )
    order_by = sort_field_expr_to_order_by(expr=expr)
    assert isinstance(order_by, OrderByMetadataField)
    assert order_by.field_name == "custom_metric"


def test_image_sort_expr_to_order_by__evaluation_metric_ascending() -> None:
    expr = EvaluationMetricSortExpr(
        evaluation_run_name="run1",
        metric_name="score",
        direction=SortDirection.asc,
    )
    order_by = image_sort_expr_to_order_by(expr=expr)
    assert isinstance(order_by, OrderByEvaluationMetricField)
    assert order_by.evaluation_run_name == "run1"
    assert order_by.metric_name == "score"
    assert order_by.ascending is True


def test_image_sort_expr_to_order_by__evaluation_metric_descending() -> None:
    expr = EvaluationMetricSortExpr(
        evaluation_run_name="run1",
        metric_name="precision",
        direction=SortDirection.desc,
    )
    order_by = image_sort_expr_to_order_by(expr=expr)
    assert isinstance(order_by, OrderByEvaluationMetricField)
    assert order_by.evaluation_run_name == "run1"
    assert order_by.metric_name == "precision"
    assert order_by.ascending is False


def test_image_sort_expr_discriminated_union__routes_to_evaluation_metric() -> None:
    adapter: TypeAdapter[ImageSortExpr] = TypeAdapter(ImageSortExpr)
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


def test_image_sort_expr_discriminated_union__routes_to_sort_field_expr() -> None:
    adapter: TypeAdapter[ImageSortExpr] = TypeAdapter(ImageSortExpr)
    expr = adapter.validate_python(
        {
            "source": "image",
            "field_name": "file_name",
            "direction": "asc",
        }
    )
    assert isinstance(expr, ImageSortFieldExpr)
    assert expr.field_name == "file_name"
