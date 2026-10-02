"""EvaluationClassMetric model — per-class summary metric values of a run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Field, SQLModel


class EvaluationClassMetricTable(SQLModel, table=True):
    """One row per (evaluation_run, annotation label, metric_name) tuple.

    Holds per-class summary metrics such as the average precision of a class at one
    IoU threshold. Means over classes or thresholds are not stored.
    """

    __tablename__ = "evaluation_class_metric"

    evaluation_run_id: UUID = Field(
        primary_key=True,
        foreign_key="evaluation_run.id",
        index=True,
    )
    # Not a foreign key, so that stored metrics never block deleting a label.
    annotation_label_id: UUID = Field(primary_key=True)
    metric_name: str = Field(primary_key=True)
    value: float


class EvaluationClassMetricCreate(SQLModel):
    """Evaluation class metric payload used when creating new rows."""

    evaluation_run_id: UUID
    annotation_label_id: UUID
    metric_name: str
    value: float
