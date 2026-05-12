"""EvaluationSampleMetric model — per-image scalar metric values."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Field, SQLModel


class EvaluationSampleMetricTable(SQLModel, table=True):
    """One row per (evaluation_run, sample, metric_name) tuple."""

    __tablename__ = "evaluation_sample_metric"

    evaluation_run_id: UUID = Field(
        primary_key=True,
        foreign_key="evaluation_run.id",
        index=True,
    )
    sample_id: UUID = Field(
        primary_key=True,
        foreign_key="sample.sample_id",
        index=True,
    )
    metric_name: str = Field(primary_key=True)
    value: float


class EvaluationSampleMetricBoundsView(BaseModel):
    """Min/max value bounds for a single metric across all samples in a run."""

    metric_name: str
    min_value: float
    max_value: float


class EvaluationRunMetricsInfoView(BaseModel):
    """Metric bounds for all metrics in a single evaluation run."""

    run_name: str
    metrics: list[EvaluationSampleMetricBoundsView]


class EvaluationSampleMetricCreate(SQLModel):
    """Evaluation sample metric payload used when creating new rows."""

    evaluation_run_id: UUID
    sample_id: UUID
    metric_name: str
    value: float
