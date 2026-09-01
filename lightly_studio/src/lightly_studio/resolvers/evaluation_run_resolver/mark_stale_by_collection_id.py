"""Mark evaluation runs as stale when their annotation collections change."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import update
from sqlmodel import Session, col

from lightly_studio.models.evaluation_run import EvaluationRunTable


def mark_stale_by_collection_id(session: Session, collection_id: UUID) -> None:
    """Set ``stale_since`` on every evaluation run referencing *collection_id*.

    Matches runs whose ``gt_annotation_collection_id`` or
    ``pred_annotation_collection_id`` equals the given collection.  Calling this
    function multiple times updates ``stale_since`` to the latest timestamp.
    """
    now = datetime.now(timezone.utc)
    stmt = (
        update(EvaluationRunTable)
        .where(
            (col(EvaluationRunTable.gt_annotation_collection_id) == collection_id)
            | (col(EvaluationRunTable.pred_annotation_collection_id) == collection_id)
        )
        .values(stale_since=now)
    )
    session.execute(stmt)
    session.commit()
