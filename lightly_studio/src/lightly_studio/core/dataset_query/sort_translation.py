"""Translate sort keys into dataset-query order-by expressions."""

from __future__ import annotations

from collections.abc import Mapping

from lightly_studio.core.dataset_query.field import Field
from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByExpression,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.errors import QueryExprError
from lightly_studio.models.sort_direction import SortDirection

_SORT_FIELDS: dict[tuple[str, str], Field] = {
    ("image", "file_name"): ImageSampleField.file_name,
    ("image", "file_path_abs"): ImageSampleField.file_path_abs,
    ("image", "created_at"): ImageSampleField.created_at,
    ("image", "width"): ImageSampleField.width,
    ("image", "height"): ImageSampleField.height,
    ("video", "file_name"): VideoSampleField.file_name,
    ("video", "file_path_abs"): VideoSampleField.file_path_abs,
    ("video", "created_at"): VideoSampleField.created_at,
    ("video", "width"): VideoSampleField.width,
    ("video", "height"): VideoSampleField.height,
    ("video", "duration_s"): VideoSampleField.duration_s,
    ("video", "fps"): VideoSampleField.fps,
    ("video_frame", "frame_number"): VideoFrameSampleField.frame_number,
    ("video_frame", "frame_timestamp_s"): VideoFrameSampleField.frame_timestamp_s,
    ("video_frame", "frame_timestamp_pts"): VideoFrameSampleField.frame_timestamp_pts,
    ("video_frame", "rotation_deg"): VideoFrameSampleField.rotation_deg,
}


def sort_fields() -> Mapping[tuple[str, str], Field]:
    """Return the sample fields that a sort can use, by (table, name)."""
    return _SORT_FIELDS


def sort_to_order_by(
    key: tuple[str, str],
    direction: SortDirection,
) -> OrderByExpression:
    """Translate a (source, field_name) key and direction to an OrderByExpression.

    Args:
        key: A (source, field_name) tuple identifying the sort field (e.g.,
            ``("image", "width")`` or ``("metadata", "brightness")``).
        direction: Sort direction, either "asc" or "desc".

    Returns:
        An OrderByExpression ready to be applied to a database query.

    Raises:
        QueryExprError: If the key does not correspond to a known sort field.
    """
    order_by: OrderByExpression
    source, field_name = key
    if source == "metadata":
        order_by = OrderByMetadataField(field_name=field_name)
    elif key in _SORT_FIELDS:
        order_by = OrderByField(_SORT_FIELDS[key])
    else:
        raise QueryExprError(f"Unknown sort field: {key[0]}.{key[1]}")
    if direction == "desc":
        order_by.desc()
    return order_by


def evaluation_metric_sort_to_order_by(
    evaluation_run_name: str,
    metric_name: str,
    direction: SortDirection,
) -> OrderByExpression:
    """Translate an evaluation run name, metric name, and direction to an OrderByExpression.

    Args:
        evaluation_run_name: The name of the evaluation run to sort by.
        metric_name: The metric name to sort by.
        direction: Sort direction, either "asc" or "desc".

    Returns:
        An OrderByExpression ready to be applied to a database query.
    """
    order_by: OrderByExpression = OrderByEvaluationMetricField(
        evaluation_run_name=evaluation_run_name,
        metric_name=metric_name,
    )
    if direction == "desc":
        order_by.desc()
    return order_by
