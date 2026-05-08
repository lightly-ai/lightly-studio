"""Query evaluation sample metrics by evaluation run."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.evaluation_sample_metric import (
    EvaluationSampleMetricBoundsView,
    EvaluationSampleMetricTable,
)


def get_metric_list_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
) -> list[EvaluationSampleMetricBoundsView]:
    """Return min/max bounds for each metric in the given evaluation run."""
    stmt = (
        select(
            col(EvaluationSampleMetricTable.metric_name),
            func.min(EvaluationSampleMetricTable.value).label("min_value"),
            func.max(EvaluationSampleMetricTable.value).label("max_value"),
        )
        .where(col(EvaluationSampleMetricTable.evaluation_run_id) == evaluation_run_id)
        .group_by(col(EvaluationSampleMetricTable.metric_name))
    )
    rows = session.execute(stmt).mappings().all()
    return [
        EvaluationSampleMetricBoundsView(
            metric_name=row["metric_name"],
            min_value=row["min_value"],
            max_value=row["max_value"],
        )
        for row in rows
    ]
