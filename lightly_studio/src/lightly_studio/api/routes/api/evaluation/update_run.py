"""Update an evaluation's parameters and recompute its results."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.evaluation.image_dataset_evaluate import EvaluationResult
from lightly_studio.resolvers import evaluation_run_resolver
from lightly_studio.services.evaluation_service import update_evaluation_run

update_run_router = APIRouter()


@update_run_router.put("/evaluation/runs/{run_id}", response_model=EvaluationResult)
def update_run(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    run_id: Annotated[UUID, Path(title="Evaluation run ID")],
    request: update_evaluation_run.EvaluationRunUpdate,
) -> EvaluationResult:
    """Replace settings and results, preserving the run and recovering on failure."""
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None or run.dataset_id != dataset_id:
        raise NotFoundError(f"Evaluation run {run_id} not found in dataset {dataset_id}.")
    return update_evaluation_run.update_evaluation_run(session=session, run=run, settings=request)
