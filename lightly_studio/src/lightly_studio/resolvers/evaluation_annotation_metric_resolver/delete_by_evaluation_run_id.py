"""Delete all annotation metrics for an evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricTable


def delete_by_evaluation_run_id(session: Session, evaluation_run_id: UUID) -> None:
    """Delete all annotation metrics for the given evaluation run.

    The DELETE is executed within the current transaction but not committed.
    The caller is responsible for committing or rolling back.
    """
    session.exec(
        delete(EvaluationAnnotationMetricTable).where(
            col(EvaluationAnnotationMetricTable.evaluation_run_id) == evaluation_run_id
        )
    )
