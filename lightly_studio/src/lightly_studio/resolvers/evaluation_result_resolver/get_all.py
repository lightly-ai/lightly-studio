"""Query evaluation results for a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_result import EvaluationResultTable


def get_all(
    session: Session,
    dataset_id: UUID,
) -> list[EvaluationResultTable]:
    """Return all evaluation results for a dataset, newest first."""
    stmt = (
        select(EvaluationResultTable)
        .where(col(EvaluationResultTable.dataset_id) == dataset_id)
        .order_by(col(EvaluationResultTable.created_at).desc())
    )
    return list(session.exec(stmt).all())


def get_by_id(
    session: Session,
    evaluation_id: UUID,
) -> EvaluationResultTable | None:
    """Return a single evaluation result by ID."""
    return session.get(EvaluationResultTable, evaluation_id)
