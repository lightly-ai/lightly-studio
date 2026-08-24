"""Clear stale_since for an evaluation run after a successful recompute."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, col

from lightly_studio.models.evaluation_run import EvaluationRunTable


def clear_stale_since(
    session: Session,
    evaluation_run_id: UUID,
    *,
    expected_stale_since: datetime | None,
) -> None:
    """Set ``stale_since`` to ``None`` only if it still equals ``expected_stale_since``.

    This prevents a concurrent ``mark_stale_by_collection_id`` call from being
    silently overwritten when recomputation finishes after annotations changed.
    """
    conditions = [col(EvaluationRunTable.id) == evaluation_run_id]
    if expected_stale_since is None:
        conditions.append(col(EvaluationRunTable.stale_since).is_(None))
    else:
        conditions.append(col(EvaluationRunTable.stale_since) == expected_stale_since)
    stmt = update(EvaluationRunTable).where(*conditions).values(stale_since=None)
    session.execute(stmt)
    session.commit()
