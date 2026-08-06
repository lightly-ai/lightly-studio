"""Sorting models for annotation grids.

Kept separate from the image sort union in ``models.sort``: that union's members bind to
image-specific joins that are invalid against an annotation-rooted query, so sharing it
would let the API accept requests it cannot serve.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from lightly_studio.models.sort_direction import SortDirection


class AnnotationSortFieldSource(str, Enum):
    """Source of the value to sort annotations by."""

    annotation_evaluation_metric = "annotation_evaluation_metric"


class AnnotationEvaluationMetricSortExpr(BaseModel):
    """A sorting expression for a per-annotation evaluation metric.

    Attributes:
        source: Always ``"annotation_evaluation_metric"`` (discriminator for the union).
        evaluation_run_id: ID of the evaluation run holding the metric.
        metric_name: Metric name as stored, e.g. ``"iou"`` or ``"disagreement"``. The
            direction carries the polarity, which differs by task type.
        direction: The sort direction, either ascending or descending.
    """

    source: Literal[AnnotationSortFieldSource.annotation_evaluation_metric] = (
        AnnotationSortFieldSource.annotation_evaluation_metric
    )
    evaluation_run_id: UUID
    metric_name: str
    direction: SortDirection


# One member today. The discriminator is present from day one so annotation-intrinsic
# sort fields can be added as further union members without a breaking change.
AnnotationSortExpr = AnnotationEvaluationMetricSortExpr
