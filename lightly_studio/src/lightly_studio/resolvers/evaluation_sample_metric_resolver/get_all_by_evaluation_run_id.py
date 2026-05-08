"""Query evaluation sample metrics by evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable


def get_all_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
) -> list[EvaluationSampleMetricTable]:
    """Return all sample metrics for a given evaluation run."""
    stmt = select(EvaluationSampleMetricTable).where(
        col(EvaluationSampleMetricTable.evaluation_run_id) == evaluation_run_id
    )
    return list(session.exec(stmt).all())
