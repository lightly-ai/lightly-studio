"""Configs and results of the evaluation tasks."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, ValidationInfo, field_validator

from lightly_studio.models.evaluation_run import EvaluationTaskType


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


EvaluationConfig = (
    ObjectDetectionEvaluationConfig
    | ClassificationEvaluationConfig
    | InstanceSegmentationEvaluationConfig
    | SemanticSegmentationEvaluationConfig
)


class EvaluationTask(BaseModel):
    """An evaluation run to create.

    Attributes:
        task_type: The type of the evaluation task.
        name: The name of the evaluation run.
        gt_annotation_source: The annotation source with the ground truth annotations.
        pred_annotation_source: The annotation source with the predictions.
        config: The config of the task. Its type must agree with `task_type`.
    """

    task_type: EvaluationTaskType
    name: str
    gt_annotation_source: str
    pred_annotation_source: str
    config: EvaluationConfig

    @field_validator("config", mode="before")
    @classmethod
    def _validate_config_for_task_type(cls, config: object, info: ValidationInfo) -> object:
        """Validate with the config class of the task type. The union cannot select the class."""
        if "task_type" not in info.data:
            return config
        return _CONFIG_CLASS_BY_TASK_TYPE[info.data["task_type"]].model_validate(config)


_CONFIG_CLASS_BY_TASK_TYPE: dict[EvaluationTaskType, type[EvaluationConfig]] = {
    EvaluationTaskType.OBJECT_DETECTION: ObjectDetectionEvaluationConfig,
    EvaluationTaskType.CLASSIFICATION: ClassificationEvaluationConfig,
    EvaluationTaskType.SEMANTIC_SEGMENTATION: SemanticSegmentationEvaluationConfig,
    EvaluationTaskType.INSTANCE_SEGMENTATION: InstanceSegmentationEvaluationConfig,
}
