"""Sorting models for annotation grids."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from lightly_studio.models.sort_direction import SortDirection


class AnnotationEvaluationMetricSortExpr(BaseModel):
    """A sorting expression for a per-annotation evaluation metric.

    Attributes:
        source: Always ``"annotation_evaluation_metric"``.
        evaluation_run_id: ID of the evaluation run holding the metric.
        metric_name: Metric name as stored, e.g. ``"iou"`` or ``"disagreement"``. The
            direction carries the polarity, which differs by task type.
        direction: The sort direction, either ascending or descending.
    """

    # TODO(Jonas, 08/2026): Promote to a discriminated union when a second annotation
    # sort field lands.
    source: Literal["annotation_evaluation_metric"] = "annotation_evaluation_metric"
    evaluation_run_id: UUID
    metric_name: str
    direction: SortDirection
