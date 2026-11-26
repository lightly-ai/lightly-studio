"""Configs and results of the evaluation tasks."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ObjectDetectionEvaluationConfig(BaseModel):
    """Configuration for object-detection evaluation runs.

    Attributes:
        iou_threshold: IoU threshold used by object-detection evaluators.
            Stored in the run config for reproducibility.
        classwise: If True, match predictions and ground truths only within the
            same annotation class. If False, match globally across all annotation classes.
        compute_average_precision: If True, also store the per-class average
            precision at the COCO IoU thresholds. Off by default, because it matches
            the annotations once per threshold. Average precision always matches
            predictions within their own class, even if ``classwise`` is False.
    """

    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    classwise: bool = True
    compute_average_precision: bool = False


class EvaluationResult(BaseModel):
    """Summary of the inputs used by an evaluation run.

    Returned by every task method on ``ImageDatasetEvaluate``. The field set is
    shared across tasks (object detection, classification, segmentation).

    Attributes:
        evaluation_run_id: ID of the persisted evaluation run.
        sample_count: Number of samples included in the evaluation.
        gt_annotation_count: Number of ground truth annotations used.
        pred_annotation_count: Number of prediction annotations used.
    """

    evaluation_run_id: UUID
    sample_count: int
    gt_annotation_count: int
    pred_annotation_count: int


class ClassificationEvaluationConfig(BaseModel):
    """Configuration for classification evaluation runs.

    Currently has no fields. Placeholder for future task-specific options.
    """


class SemanticSegmentationEvaluationConfig(BaseModel):
    """Configuration for semantic-segmentation evaluation runs.

    Currently has no fields. Placeholder for future task-specific options.
    """


class InstanceSegmentationEvaluationConfig(BaseModel):
    """Configuration for instance-segmentation evaluation runs.

    Attributes:
        iou_threshold: Mask IoU threshold used to match predictions to ground
            truths. Stored in the run config for reproducibility.
        classwise: If True, match predictions and ground truths only within the
            same annotation class. If False, match across all annotation classes.
    """

    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    classwise: bool = True
