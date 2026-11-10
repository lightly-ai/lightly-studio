"""Models for training runs that train a model with LightlyTrain."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

DEFAULT_TRAINING_MODEL_NAME = "dinov3/vitt16-ltdetr-coco"
DEFAULT_TRAINING_STEPS = 100


class TrainingRunStatus(str, Enum):
    """The stage of a training run."""

    TRAINING = "training"
    PREDICTING = "predicting"
    INGESTING = "ingesting"
    EVALUATING = "evaluating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ACTIVE_TRAINING_RUN_STATUSES = frozenset(
    (
        TrainingRunStatus.TRAINING,
        TrainingRunStatus.PREDICTING,
        TrainingRunStatus.INGESTING,
        TrainingRunStatus.EVALUATING,
    )
)


class TrainingRunCreate(BaseModel):
    """Input to start a training run."""

    train_tag_id: UUID
    val_tag_id: UUID
    gt_annotation_collection_id: UUID
    """The annotation source with the ground truth annotations."""
    model_name: str = DEFAULT_TRAINING_MODEL_NAME
    steps: int = Field(default=DEFAULT_TRAINING_STEPS, ge=1)


class TrainingRunView(BaseModel):
    """A training run as the API returns it."""

    training_run_id: UUID
    collection_id: UUID
    name: str
    """The name of the run. The annotation source with the predictions has the same name."""
    status: TrainingRunStatus
    model_name: str
    steps: int
    train_sample_count: int
    val_sample_count: int
    created_at: datetime
    current_step: Optional[int] = None
    total_steps: Optional[int] = None
    train_loss: Optional[float] = None
    evaluation_run_id: Optional[UUID] = None
    error: Optional[str] = None
