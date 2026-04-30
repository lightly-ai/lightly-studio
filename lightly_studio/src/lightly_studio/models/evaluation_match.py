"""EvaluationMatch model — per-annotation match result for one evaluation run."""

from __future__ import annotations

from enum import Enum
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MatchType(str, Enum):
    """Classification of one annotation in an evaluation: TP, FP, or FN."""

    TP = "TP"
    FP = "FP"
    FN = "FN"


class EvaluationMatchTable(SQLModel, table=True):
    """One row per annotation involved in an evaluation run.

    TPs have both pred_annotation_id and gt_annotation_id set plus an iou value.
    FPs have only pred_annotation_id set (no matching GT found).
    FNs have only gt_annotation_id set (GT was never matched by any prediction).

    sample_id is the parent image sample — used for per-image TP/FP/FN aggregation
    and for filtering by tag when computing per-subset metrics.
    """

    __tablename__ = "evaluation_match"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_result_id: UUID = Field(foreign_key="evaluation_result.id", index=True)
    sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
    pred_annotation_id: UUID | None = Field(default=None, foreign_key="annotation_base.sample_id")
    gt_annotation_id: UUID | None = Field(default=None, foreign_key="annotation_base.sample_id")
    iou: float | None = None
    match_type: MatchType
