"""Persist the frozen sample snapshot for an evaluation run."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_result_sample import EvaluationResultSampleTable


def persist_sample_ids(
    session: Session,
    evaluation_result_id: UUID,
    sample_ids: Sequence[UUID],
) -> None:
    """Persist the frozen sample snapshot for one evaluation run."""
    rows = [
        EvaluationResultSampleTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=sample_id,
        )
        for sample_id in sample_ids
    ]
    session.add_all(rows)
    session.flush()
