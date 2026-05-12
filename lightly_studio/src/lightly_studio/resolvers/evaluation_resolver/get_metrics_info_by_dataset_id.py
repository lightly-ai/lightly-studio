"""Query evaluation metric bounds grouped by run for a dataset."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlmodel import Session, col, func, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.models.evaluation_sample_metric import (
    EvaluationRunMetricsInfoView,
    EvaluationSampleMetricBoundsView,
    EvaluationSampleMetricTable,
)


def get_metrics_info_by_dataset_id(
    session: Session,
    dataset_id: UUID,
) -> list[EvaluationRunMetricsInfoView]:
    """Return metric bounds for all evaluation runs in a dataset, grouped by run.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.

    Returns:
        List of evaluation run metric info objects, each containing the run name
        and the min/max bounds for every metric recorded in that run.
    """
    stmt = (
        select(  # type: ignore[call-overload]
            col(EvaluationRunTable.id),
            col(EvaluationRunTable.name),
            col(EvaluationSampleMetricTable.metric_name),
            func.min(EvaluationSampleMetricTable.value).label("min_value"),
            func.max(EvaluationSampleMetricTable.value).label("max_value"),
        )
        .join(
            CollectionTable,
            col(EvaluationRunTable.gt_annotation_collection_id)
            == col(CollectionTable.collection_id),
        )
        .join(
            EvaluationSampleMetricTable,
            col(EvaluationSampleMetricTable.evaluation_run_id) == col(EvaluationRunTable.id),
        )
        .where(col(CollectionTable.dataset_id) == dataset_id)
        .group_by(
            col(EvaluationRunTable.id),
            col(EvaluationRunTable.name),
            col(EvaluationSampleMetricTable.metric_name),
        )
    )

    rows = session.execute(stmt).mappings().all()

    run_names: dict[UUID, str] = {}
    run_metrics: dict[UUID, list[EvaluationSampleMetricBoundsView]] = defaultdict(list)
    for row in rows:
        run_id = row["id"]
        run_names[run_id] = row["name"]
        run_metrics[run_id].append(
            EvaluationSampleMetricBoundsView(
                metric_name=row["metric_name"],
                min_value=row["min_value"],
                max_value=row["max_value"],
            )
        )

    return [
        EvaluationRunMetricsInfoView(run_name=run_names[run_id], metrics=metrics)
        for run_id, metrics in run_metrics.items()
    ]
