"""Aggregate TP/FP/FN counts per sample for a given evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.evaluation_match import EvaluationMatchTable


def get_sample_counts(
    session: Session,
    evaluation_result_id: UUID,
) -> dict[UUID, dict[str, int]]:
    """Return per-image TP/FP/FN counts for an evaluation run.

    Returns:
        Dict mapping sample_id → {"tp": int, "fp": int, "fn": int}.
        Only samples that appear in the match table are included.
    """
    rows = session.exec(
        select(
            EvaluationMatchTable.sample_id,
            EvaluationMatchTable.match_type,
            func.count().label("count"),
        )
        .where(col(EvaluationMatchTable.evaluation_result_id) == evaluation_result_id)
        .group_by(
            col(EvaluationMatchTable.sample_id),
            col(EvaluationMatchTable.match_type),
        )
    ).all()

    result: dict[UUID, dict[str, int]] = {}
    for sample_id, match_type, count in rows:
        entry = result.setdefault(sample_id, {"tp": 0, "fp": 0, "fn": 0})
        entry[match_type.lower()] = count

    return result
