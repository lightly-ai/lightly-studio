"""EvaluationAnnotationMatch model — per-annotation-pair matching results."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class EvaluationAnnotationMatchTable(SQLModel, table=True):
    """One row per annotation pair matched during an evaluation run.

    For TP rows both gt_annotation_id and pred_annotation_id are set.
    For FN rows pred_annotation_id is NULL.
    For FP rows gt_annotation_id is NULL.
    """

    __tablename__ = "evaluation_annotation_match"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    evaluation_run_id: UUID = Field(
        foreign_key="evaluation_run.id",
        index=True,
    )
    # Nullable because FP matches have no GT, FN matches have no prediction.
    gt_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
    )
    pred_annotation_id: UUID | None = Field(
        default=None,
        foreign_key="annotation_base.sample_id",
    )
    sample_id: UUID = Field(foreign_key="sample.sample_id", index=True)
    gt_label_id: UUID | None = Field(default=None)
    pred_label_id: UUID | None = Field(default=None)
    iou: float | None = Field(default=None)


class EvaluationAnnotationMatchCreate(SQLModel):
    """Payload for creating a new annotation match row."""

    evaluation_run_id: UUID
    gt_annotation_id: UUID | None
    pred_annotation_id: UUID | None
    sample_id: UUID
    gt_label_id: UUID | None
    pred_label_id: UUID | None
    iou: float | None


class ConfusionMatrixCell(SQLModel):
    """One cell of the confusion matrix."""

    gt_label_id: UUID | None
    pred_label_id: UUID | None
    count: int
