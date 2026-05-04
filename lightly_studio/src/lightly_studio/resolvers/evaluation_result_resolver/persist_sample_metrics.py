"""Persist per-sample metric rows for an evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import (
    NULL_LABEL_ID,
    EvaluationSampleMetricTable,
)


def persist_sample_metrics(
    session: Session,
    evaluation_result_id: UUID,
    metrics: dict[tuple[UUID, UUID | None], dict[str, float]],
) -> None:
    """Bulk-insert sample metric rows without committing.

    Args:
        session: Database session.
        evaluation_result_id: FK to the parent evaluation result row.
        metrics: Maps (sample_id, label_id) → {metric_name: value}.
            label_id=None means the row is an aggregate across all classes.
    """
    rows = [
        EvaluationSampleMetricTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=sample_id,
            label_id=label_id if label_id is not None else NULL_LABEL_ID,
            metric_name=metric_name,
            value=value,
        )
        for (sample_id, label_id), metric_dict in metrics.items()
        for metric_name, value in metric_dict.items()
    ]
    session.add_all(rows)
    session.flush()
