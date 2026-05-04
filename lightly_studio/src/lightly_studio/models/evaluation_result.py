"""EvaluationResult model — persisted output of one evaluation run."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Union
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EvaluationTaskType(str, Enum):
    """Supported evaluation task types."""

    OBJECT_DETECTION = "object_detection"
    CLASSIFICATION = "classification"
    INSTANCE_SEGMENTATION = "instance_segmentation"


class EvaluationResultTable(SQLModel, table=True):
    """One row per evaluation run (one prediction collection against one GT collection).

    metrics structure:
        {
            "all": { ... task-specific metrics for the frozen sample snapshot ... },
        }
    """

    __tablename__ = "evaluation_result"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    name: str
    gt_collection_id: UUID = Field(foreign_key="annotation_collection.id")
    prediction_collection_id: UUID = Field(foreign_key="annotation_collection.id")
    task_type: EvaluationTaskType
    iou_threshold: float = 0.5
    confidence_threshold: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ObjectDetectionPerClassMetrics(BaseModel):
    """Per-class object detection metrics."""

    ap: float
    precision: float
    recall: float
    f1: float


class ObjectDetectionEvaluationMetrics(BaseModel):
    """Aggregate object detection metrics for one subset (e.g. "all" or a tag name)."""

    precision: float
    recall: float
    f1: float
    mAP: float  # noqa: N815
    per_class_metrics: dict[str, ObjectDetectionPerClassMetrics] = {}


class ClassificationPerClassMetrics(BaseModel):
    """Per-class classification metrics."""

    precision: float
    recall: float
    f1: float
    support: int


class ClassificationEvaluationMetrics(BaseModel):
    """Aggregate classification metrics for one subset."""

    accuracy: float
    precision: float
    recall: float
    f1: float
    per_class_metrics: dict[str, ClassificationPerClassMetrics] = {}


class InstanceSegmentationPerClassMetrics(BaseModel):
    """Per-class instance segmentation metrics."""

    ap: float
    precision: float
    recall: float
    f1: float


class InstanceSegmentationEvaluationMetrics(BaseModel):
    """Aggregate instance segmentation metrics for one subset."""

    precision: float
    recall: float
    f1: float
    mAP: float  # noqa: N815
    per_class_metrics: dict[str, InstanceSegmentationPerClassMetrics] = {}


EvaluationMetrics = Union[
    ObjectDetectionEvaluationMetrics,
    ClassificationEvaluationMetrics,
    InstanceSegmentationEvaluationMetrics,
]


class EvaluationResultView(BaseModel):
    """Read-only view of a persisted EvaluationResultTable row."""

    model_config = {"from_attributes": True}

    id: UUID
    dataset_id: UUID
    name: str
    gt_collection_id: UUID
    prediction_collection_id: UUID
    task_type: EvaluationTaskType
    iou_threshold: float
    confidence_threshold: float
    metrics: dict[str, EvaluationMetrics]
    created_at: datetime
