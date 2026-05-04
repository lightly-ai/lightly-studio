"""EvaluationSampleMetric model — per-image scalar metric values."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel

NULL_LABEL_ID = UUID(int=0)
"""Sentinel UUID used when label_id is None (aggregate across all classes)."""


class EvaluationSampleMetricTable(SQLModel, table=True):
    """One row per (evaluation, sample, label, metric_name) tuple.

    label_id stores NULL_LABEL_ID (all-zero UUID) for aggregate rows that
    span all classes. Per-class rows store the real annotation_label_id.
    """

    __tablename__ = "evaluation_sample_metric"

    evaluation_result_id: UUID = Field(
        primary_key=True,
        foreign_key="evaluation_result.id",
        index=True,
    )
    sample_id: UUID = Field(
        primary_key=True,
        foreign_key="sample.sample_id",
        index=True,
    )
    label_id: UUID = Field(
        primary_key=True,
        default=NULL_LABEL_ID,
        index=True,
    )
    metric_name: str = Field(primary_key=True)
    value: float
