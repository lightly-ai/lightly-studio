"""Delete an evaluation and its results."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.resolvers import evaluation_run_resolver

delete_run_router = APIRouter()


@delete_run_router.delete("/evaluation/runs/{run_id}", status_code=204)
def delete_run(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    run_id: Annotated[UUID, Path(title="Evaluation run ID")],
) -> None:
    """Delete a run from its dataset without deleting annotations."""
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None or run.dataset_id != dataset_id:
        raise NotFoundError(f"Evaluation run {run_id} not found in dataset {dataset_id}.")
    evaluation_run_resolver.delete(session=session, run=run)
