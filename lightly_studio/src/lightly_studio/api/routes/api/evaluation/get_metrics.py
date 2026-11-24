"""Route to get the aggregate metrics of several evaluation runs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path, Query

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.evaluation_metrics import EvaluationRunMetricsView
from lightly_studio.services import evaluation_service

get_metrics_router = APIRouter()


@get_metrics_router.get(
    "/evaluation/runs/metrics",
    response_model=list[EvaluationRunMetricsView],
)
def get_evaluation_runs_metrics(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    run_ids: Annotated[list[UUID], Query(min_length=1)],
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
) -> list[EvaluationRunMetricsView]:
    """Get the aggregate metrics of evaluation runs, for comparison.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.
        run_ids: The evaluation runs, in the order of the response.
        tag_ids: Tags to compare the runs on. Each run gets one slice for each tag.

    Returns:
        The metrics, the evaluated sample set, and the tag slices of each run.
    """
    return evaluation_service.get_runs_metrics(
        session=session,
        dataset_id=dataset_id,
        evaluation_run_ids=run_ids,
        tag_ids=tag_ids or [],
    )
