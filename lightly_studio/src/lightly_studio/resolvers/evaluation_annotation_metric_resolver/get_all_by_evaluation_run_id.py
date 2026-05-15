"""Query evaluation annotation metrics by evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable


def get_all_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
) -> list[EvaluationAnnotationMetricTable]:
    """Return all annotation metrics for a given evaluation run."""
    stmt = select(EvaluationAnnotationMetricTable).where(
        col(EvaluationAnnotationMetricTable.evaluation_run_id) == evaluation_run_id
    )
    return list(session.exec(stmt).all())
