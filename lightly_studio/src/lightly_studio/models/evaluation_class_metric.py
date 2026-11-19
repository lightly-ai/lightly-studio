"""EvaluationClassMetric model — per-class summary metric values of a run."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import JSON, Column, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# JSONB on PostgreSQL, because the plain JSON type cannot be part of a unique key there.
_CONFIG_OVERRIDE_TYPE = JSON().with_variant(JSONB(), "postgresql")


class EvaluationClassMetricTable(SQLModel, table=True):
    """One row per (evaluation_run, annotation label, metric_name, config_override) tuple.

    Holds per-class summary metrics such as the average precision of a class. Means over
    classes are not stored.
    """

    __tablename__ = "evaluation_class_metric"
    # A unique constraint, not a composite primary key, because the ORM cannot hash a dict.
    __table_args__ = (
        UniqueConstraint(
            "evaluation_run_id", "annotation_label_id", "metric_name", "config_override"
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_run_id: UUID = Field(foreign_key="evaluation_run.id", index=True)
    annotation_label_id: UUID = Field(
        foreign_key="annotation_label.annotation_label_id", index=True
    )
    metric_name: str
    # Config fields that differ from the run's config_json. Empty for the run's own config.
    config_override: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(_CONFIG_OVERRIDE_TYPE, nullable=False),
    )
    value: float


class EvaluationClassMetricCreate(SQLModel):
    """Evaluation class metric payload used when creating new rows."""

    evaluation_run_id: UUID
    annotation_label_id: UUID
    metric_name: str
    config_override: dict[str, Any] = Field(default_factory=dict)
    value: float

    @field_validator("config_override")
    @classmethod
    def _sort_config_override_keys(cls, value: dict[str, Any]) -> dict[str, Any]:
        """Sort the keys, because DuckDB compares JSON values as text in the unique key."""
        return dict(sorted(value.items()))
