"""Persist per-annotation match records for an evaluation run."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_match import EvaluationMatchTable, MatchType


class MatchRecordLike(Protocol):
    """Protocol for persisted per-annotation match records."""

    sample_id: UUID
    pred_id: UUID | None
    gt_id: UUID | None
    iou: float | None
    match_type: str


def persist_matches(
    session: Session,
    evaluation_result_id: UUID,
    records: Sequence[MatchRecordLike],
) -> None:
    """Persist task-specific match records into the shared evaluation table."""
    rows = [
        EvaluationMatchTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=record.sample_id,
            pred_annotation_id=record.pred_id,
            gt_annotation_id=record.gt_id,
            iou=record.iou,
            match_type=MatchType(record.match_type),
        )
        for record in records
    ]
    session.add_all(rows)
    session.flush()
