"""Compute the NxN confusion matrix for an evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.evaluation_annotation_match import (
    ConfusionMatrixCell,
    EvaluationAnnotationMatchTable,
)


def get_confusion_matrix(
    session: Session,
    evaluation_run_id: UUID,
) -> list[ConfusionMatrixCell]:
    """Return confusion matrix cells grouped by (gt_label_id, pred_label_id)."""
    stmt = (
        select(
            col(EvaluationAnnotationMatchTable.gt_label_id),
            col(EvaluationAnnotationMatchTable.pred_label_id),
            func.count().label("count"),
        )
        .where(col(EvaluationAnnotationMatchTable.evaluation_run_id) == evaluation_run_id)
        .group_by(
            col(EvaluationAnnotationMatchTable.gt_label_id),
            col(EvaluationAnnotationMatchTable.pred_label_id),
        )
    )
    rows = session.exec(stmt).all()
    return [
        ConfusionMatrixCell(gt_label_id=r[0], pred_label_id=r[1], count=r[2]) for r in rows
    ]
