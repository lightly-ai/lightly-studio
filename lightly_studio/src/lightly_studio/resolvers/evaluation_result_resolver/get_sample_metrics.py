"""Return per-sample metric values for a given evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_sample_metric import (
    NULL_LABEL_ID,
    EvaluationSampleMetricTable,
)


def get_sample_metrics(
    session: Session,
    evaluation_result_id: UUID,
    label_id: UUID | None = None,
) -> dict[UUID, dict[str, float]]:
    """Return {sample_id: {metric_name: value}} for the given evaluation run.

    When label_id is None, returns only aggregate rows (stored with NULL_LABEL_ID).
    When label_id is a real UUID, returns only rows for that specific class.
    """
    db_label_id = label_id if label_id is not None else NULL_LABEL_ID

    rows = session.exec(
        select(EvaluationSampleMetricTable)
        .where(col(EvaluationSampleMetricTable.evaluation_result_id) == evaluation_result_id)
        .where(col(EvaluationSampleMetricTable.label_id) == db_label_id)
    ).all()

    result: dict[UUID, dict[str, float]] = {}
    for row in rows:
        entry = result.setdefault(row.sample_id, {})
        entry[row.metric_name] = row.value

    return result
