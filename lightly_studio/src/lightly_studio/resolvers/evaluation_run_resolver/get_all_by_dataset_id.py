"""Query evaluation results for a dataset."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_run import EvaluationRunTable


def get_all_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> list[EvaluationRunTable]:
    """Return all evaluation results for a dataset, newest first."""
    stmt = (
        select(EvaluationRunTable)
        .where(col(EvaluationRunTable.dataset_id) == dataset_id)
        .order_by(col(EvaluationRunTable.created_at).desc())
    )
    return list(session.exec(stmt).all())
