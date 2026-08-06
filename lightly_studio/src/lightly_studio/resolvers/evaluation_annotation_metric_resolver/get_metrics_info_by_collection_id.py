"""Query the per-annotation metrics recorded for an annotation source."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, col, or_, select

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricTable,
    EvaluationRunAnnotationMetricsInfoView,
)
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType


def get_metrics_info_by_collection_id(
    session: Session,
    collection_id: UUID,
) -> list[EvaluationRunAnnotationMetricsInfoView]:
    """Return the per-annotation metrics of every run involving an annotation source.

    Scoped to the annotation source rather than the dataset so the sort dropdown can only
    offer options the backend can resolve to a side of the run's pairing.

    Args:
        session: The database session.
        collection_id: The browsed annotation source.

    Returns:
        One entry per evaluation run involving the source, each listing its recorded
        metric names. Null metric names are filtered out, and runs left without any
        metric name are omitted.
    """
    stmt = (
        select(
            col(EvaluationRunTable.id),
            col(EvaluationRunTable.name),
            col(EvaluationRunTable.task_type),
            col(EvaluationAnnotationMetricTable.metric_name),
        )
        .join(
            EvaluationAnnotationMetricTable,
            col(EvaluationAnnotationMetricTable.evaluation_run_id) == col(EvaluationRunTable.id),
        )
        .where(
            or_(
                col(EvaluationRunTable.gt_annotation_collection_id) == collection_id,
                col(EvaluationRunTable.pred_annotation_collection_id) == collection_id,
            ),
            col(EvaluationAnnotationMetricTable.metric_name).is_not(None),
        )
        .distinct()
    )

    rows = session.execute(stmt).mappings().all()

    metric_names: dict[UUID, list[str]] = defaultdict(list)
    runs: dict[UUID, tuple[str, EvaluationTaskType]] = {}
    for row in rows:
        run_id = row["id"]
        runs[run_id] = (row["name"], row["task_type"])
        metric_names[run_id].append(row["metric_name"])

    return [
        EvaluationRunAnnotationMetricsInfoView(
            run_id=run_id,
            run_name=run_name,
            task_type=task_type,
            metric_names=sorted(metric_names[run_id]),
        )
        for run_id, (run_name, task_type) in runs.items()
    ]
