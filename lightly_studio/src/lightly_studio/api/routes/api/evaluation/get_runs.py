"""Route to list evaluation runs for a dataset."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.evaluation_run import EvaluationRunView
from lightly_studio.resolvers import collection_resolver, evaluation_run_resolver

get_runs_router = APIRouter()


@get_runs_router.get(
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
    collection_name_by_id = collection_resolver.get_names_by_ids(
        session=session,
        collection_ids={run.gt_annotation_collection_id for run in runs}
        | {run.pred_annotation_collection_id for run in runs},
    )

    return [
        EvaluationRunView(
            id=run.id,
            name=run.name,
            evaluation_run_configuration=run.config_json,
            created_at=run.created_at,
            gt_annotation_source=collection_name_by_id.get(run.gt_annotation_collection_id),
            pred_annotation_source=collection_name_by_id.get(run.pred_annotation_collection_id),
        )
        for run in runs
    ]
