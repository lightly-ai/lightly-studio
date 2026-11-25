"""Delete all class metrics for an evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, delete

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricTable


def delete_by_evaluation_run_id(session: Session, evaluation_run_id: UUID) -> None:
    """Delete all class metrics for the given evaluation run.

    The DELETE is executed within the current transaction but not committed.
    The caller is responsible for committing or rolling back.
    """
    session.exec(
        delete(EvaluationClassMetricTable).where(
            col(EvaluationClassMetricTable.evaluation_run_id) == evaluation_run_id
        )
    )
