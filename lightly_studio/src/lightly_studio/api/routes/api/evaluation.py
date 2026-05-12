"""API routes for evaluation runs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.evaluation_sample_metric import EvaluationRunMetricsInfoView
from lightly_studio.resolvers import evaluation_resolver

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluation"])


@evaluation_router.get(
    "/evaluation/metrics/info",
    response_model=list[EvaluationRunMetricsInfoView],
)
def get_evaluation_metrics_info(
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
    return evaluation_resolver.get_metrics_info_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
    )
