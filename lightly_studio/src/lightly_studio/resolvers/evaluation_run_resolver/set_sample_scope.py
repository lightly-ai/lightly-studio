"""Store the image scope of an evaluation run."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, col

from lightly_studio.models.evaluation_run import EvaluationRunTable


def set_sample_scope(
    session: Session,
    evaluation_run_id: UUID,
    sample_scope_json: dict[str, Any],
) -> None:
    """Store the collection and image filter that select the images of a run.

    A recompute of the run applies the stored scope again.
    """
    stmt = (
        update(EvaluationRunTable)
        .where(col(EvaluationRunTable.id) == evaluation_run_id)
        .values(sample_scope_json=sample_scope_json)
    )
    session.execute(stmt)
    session.commit()
