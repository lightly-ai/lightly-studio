"""EvaluationAnnotationMetricTable model — unified annotation pairing and metrics."""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlmodel import Field, SQLModel

from lightly_studio.models.evaluation_run import EvaluationTaskType


class EvaluationAnnotationSide(str, Enum):
    """Which side of an evaluation run's pairing an annotation source is."""

    GROUND_TRUTH = "ground_truth"
    PREDICTION = "prediction"


class EvaluationAnnotationMetricTable(SQLModel, table=True):
    """One row per annotation pair produced by an evaluation run.

    Match type is derivable from the nullable ID columns:
    - both IDs set  → TP
    - only pred set → FP
    - only gt set   → FN
    """

    __tablename__ = "evaluation_annotation_metric"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_run_id: UUID = Field(foreign_key="evaluation_run.id", index=True)
    sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
    pred_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
        index=True,
    )
    gt_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
        index=True,
    )
    metric_name: str | None = Field(default=None, index=True)
    value: float | None = Field(default=None)


class EvaluationAnnotationMetricInfoView(BaseModel):
    """One per-annotation metric name recorded by an evaluation run."""

    metric_name: str


class EvaluationRunAnnotationMetricsInfoView(BaseModel):
    """Per-annotation metrics recorded by one evaluation run.

    Carries no value bounds: how bounds interact with unmatched annotations, whose
    ordering value is coalesced to zero, is decided by the threshold filter.
    """

    run_id: UUID
    run_name: str
    task_type: EvaluationTaskType
    metrics: list[EvaluationAnnotationMetricInfoView]


class EvaluationAnnotationMetricCreate(SQLModel):
    """Evaluation annotation metric payload used when creating new rows."""

    evaluation_run_id: UUID
    sample_id: UUID
    pred_annotation_id: UUID | None = None
    gt_annotation_id: UUID | None = None
    metric_name: str | None = None
    value: float | None = None
