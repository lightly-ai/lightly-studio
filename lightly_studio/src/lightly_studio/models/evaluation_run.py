"""EvaluationRun model — persisted output of one evaluation run."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EvaluationTaskType(str, Enum):
    """Supported evaluation task types."""

    OBJECT_DETECTION = "object_detection"
    CLASSIFICATION = "classification"
    INSTANCE_SEGMENTATION = "instance_segmentation"


class EvaluationRunBase(SQLModel):
    """Base model for evaluation runs."""

    name: str
    # Foreign keys to the annotation collections containing Ground Truth and predicted annotations.
    gt_annotation_collection_id: UUID = Field(foreign_key="collection.collection_id")
    pred_annotation_collection_id: UUID = Field(foreign_key="collection.collection_id")

    task_type: EvaluationTaskType

    # Example config: {"iou_threshold": 0.5, "confidence_threshold": 0.0}.
    config_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )


class EvaluationRunTable(EvaluationRunBase, table=True):
    """One row per evaluation execution."""

    __tablename__ = "evaluation_run"
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EvaluationRunCreate(EvaluationRunBase):
    """Model for creating a new evaluation run."""
