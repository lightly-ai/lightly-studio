"""Query evaluation class metrics by evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_class_metric import EvaluationClassMetricTable


def get_all_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
) -> list[EvaluationClassMetricTable]:
    """Return all class metrics for a given evaluation run."""
    stmt = select(EvaluationClassMetricTable).where(
        col(EvaluationClassMetricTable.evaluation_run_id) == evaluation_run_id
    )
    return list(session.exec(stmt).all())
