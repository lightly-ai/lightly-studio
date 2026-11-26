"""Prepared input of an evaluation run and its result summary."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_task import EvaluationResult


@dataclass
class EvaluationData:
    """Inputs that every per-task metric function needs.

    Produced by ``ImageDatasetEvaluate._prepare_evaluation_data`` once per run
    and consumed by the per-task metric modules (object detection,
    classification, segmentation).

    Attributes:
        evaluation_run_id: ID of the evaluation run the metrics will be written for.
        selected_sample_ids: Parent sample IDs included in the evaluation,
            already filtered to those covered by both GT and prediction collections.
        gt_per_sample: GT annotations grouped by parent sample id.
        pred_per_sample: Prediction annotations grouped by parent sample id.
    """

    evaluation_run_id: UUID
    selected_sample_ids: set[UUID]
    gt_per_sample: dict[UUID, list[AnnotationBaseTable]]
    pred_per_sample: dict[UUID, list[AnnotationBaseTable]]


def to_evaluation_result(data: EvaluationData) -> EvaluationResult:
    """Build the result of an evaluation run from its prepared data."""
    return EvaluationResult(
        evaluation_run_id=data.evaluation_run_id,
        sample_count=len(data.selected_sample_ids),
        gt_annotation_count=sum(len(v) for v in data.gt_per_sample.values()),
        pred_annotation_count=sum(len(v) for v in data.pred_per_sample.values()),
    )
