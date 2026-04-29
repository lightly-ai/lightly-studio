"""EvaluationResult model — persisted output of a COCO metrics computation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EvaluationResultTable(SQLModel, table=True):
    """Persisted COCO evaluation result for a set of prediction collections.

    metrics structure:
        {
            "<prediction_collection_name>": {
                "all":      {"precision": 0.7, "recall": 0.8, "f1": 0.74,
                             "mAP": 0.65, "avg_confidence": 0.72},
                "<tag_name>": { ... }
            }
        }

    One row per evaluation run (one click of "Compute Metrics").
    """

    __tablename__ = "evaluation_result"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    dataset_id: UUID = Field(foreign_key="dataset.dataset_id", index=True)
    gt_collection_id: UUID = Field(foreign_key="annotation_collection.id")
    prediction_collection_ids: list[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )
    iou_threshold: float = 0.5
    confidence_threshold: float = 0.0
    metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConfusionMatrix(BaseModel):
    """Confusion matrix for matched GT/prediction pairs."""

    labels: list[str]
    matrix: list[list[int]]


class PerClassMetrics(BaseModel):
    """Per-class COCO metrics for one class."""

    ap: float
    recall: float
    f1: float


class EvaluationMetrics(BaseModel):
    """Per-subset COCO metrics."""

    precision: float
    recall: float
    f1: float
    mAP: float
    avg_confidence: float
    confusion_matrix: ConfusionMatrix | None = None
    per_class_metrics: dict[str, PerClassMetrics] | None = None


class EvaluationResultView(BaseModel):
    """Response model for an evaluation result."""

    model_config = {"from_attributes": True}

    id: UUID
    dataset_id: UUID
    gt_collection_id: UUID
    prediction_collection_ids: list[UUID]
    iou_threshold: float
    confidence_threshold: float
    metrics: dict[str, dict[str, EvaluationMetrics]]
    created_at: datetime
