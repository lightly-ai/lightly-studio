"""Return annotation result rows for a given evaluation run and sample."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_annotation_result import EvaluationAnnotationResultTable


def get_annotation_results(
    session: Session,
    evaluation_result_id: UUID,
    sample_id: UUID,
) -> list[EvaluationAnnotationResultTable]:
    """Return all annotation result rows for a given sample in an evaluation run."""
    return list(
        session.exec(
            select(EvaluationAnnotationResultTable)
            .where(
                col(EvaluationAnnotationResultTable.evaluation_result_id) == evaluation_result_id
            )
            .where(col(EvaluationAnnotationResultTable.sample_id) == sample_id)
        ).all()
    )
