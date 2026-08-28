"""Route to recompute a stale evaluation run in-place."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.evaluation.image_dataset_evaluate import EvaluationResult
from lightly_studio.resolvers import evaluation_run_resolver
from lightly_studio.services import evaluation_service

recompute_run_router = APIRouter()


@recompute_run_router.post(
    "/evaluation/runs/{run_id}/recompute",
    response_model=EvaluationResult,
)
def recompute_evaluation_run(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    run_id: Annotated[UUID, Path(title="Evaluation run ID")],
) -> EvaluationResult:
    """Recompute a stale evaluation run in-place.

    Deletes the run's existing metrics, re-runs the evaluation using the run's
    stored configuration, and resets ``stale_since`` to ``None``. The run ID
    and ``created_at`` are preserved.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.
        run_id: The evaluation run's UUID.

    Returns:
        Summary of the recomputed run, including its ID and input counts.

    Raises:
        NotFoundError: If the run does not exist or does not belong to the dataset.
    """
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None or run.dataset_id != dataset_id:
        raise NotFoundError(f"Evaluation run {run_id} not found in dataset {dataset_id}.")
    return evaluation_service.recompute_evaluation_run(session=session, run=run)
