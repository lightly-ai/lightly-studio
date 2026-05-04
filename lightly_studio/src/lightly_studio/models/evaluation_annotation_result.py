"""EvaluationAnnotationResult model — unified annotation pairing and metrics."""

from __future__ import annotations

from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class EvaluationAnnotationResultTable(SQLModel, table=True):
    """One row per annotation pair produced by an evaluation run.

    Match type is derivable from the nullable ID columns:
    - both IDs set  → TP
    - only pred set → FP
    - only gt set   → FN
    """

    __tablename__ = "evaluation_annotation_result"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_result_id: UUID = Field(foreign_key="evaluation_result.id", index=True)
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
    metrics: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
