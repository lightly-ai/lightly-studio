"""API routes for evaluation runs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.evaluation_run import EvaluationRunView
from lightly_studio.models.evaluation_sample_metric import EvaluationRunMetricsInfoView
from lightly_studio.resolvers import evaluation_run_resolver, evaluation_sample_metric_resolver

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluation"])


@evaluation_router.get(
    "/evaluation/metrics/sample/info",
    response_model=list[EvaluationRunMetricsInfoView],
)
def get_evaluation_sample_metrics_info(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
) -> list[EvaluationRunMetricsInfoView]:
    """Get metric bounds for all evaluation runs in a dataset.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.

    Returns:
        List of evaluation run metric info objects, each containing the run name
        and the min/max bounds for every metric in that run.
    """
    return evaluation_sample_metric_resolver.get_sample_metrics_info_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
    )


@evaluation_router.get(
    "/evaluation/runs",
    response_model=list[EvaluationRunView],
)
def get_evaluation_runs(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
) -> list[EvaluationRunView]:
    """Get all evaluation runs for a dataset.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.

    Returns:
        List of evaluation runs, each with id, name, and run configuration.
    """
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
    )
    return [
        EvaluationRunView(
            id=run.id,
            name=run.name,
            evaluation_run_configuration=run.config_json,
            created_at=run.created_at,
        )
        for run in runs
    ]
