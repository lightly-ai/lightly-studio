"""Query an evaluation run by ID."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_run import EvaluationRunTable


def get_by_id(
    session: Session,
    evaluation_id: UUID,
) -> EvaluationRunTable | None:
    """Return a single evaluation run by ID."""
    return session.get(EvaluationRunTable, evaluation_id)
