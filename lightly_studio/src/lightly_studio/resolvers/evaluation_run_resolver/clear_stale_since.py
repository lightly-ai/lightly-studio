"""Clear stale_since for an evaluation run after a successful recompute."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, col

from lightly_studio.models.evaluation_run import EvaluationRunTable


def clear_stale_since(session: Session, evaluation_run_id: UUID) -> None:
    """Set stale_since to None for the given evaluation run."""
    stmt = (
        update(EvaluationRunTable)
        .where(col(EvaluationRunTable.id) == evaluation_run_id)
        .values(stale_since=None)
    )
    session.execute(stmt)
    session.commit()
