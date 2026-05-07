"""EvaluationSampleMetric model — per-image scalar metric values."""

from __future__ import annotations

from uuid import UUID

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
