"""Route to get the confusion matrix for an evaluation run."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_NOT_IMPLEMENTED,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
)

get_confusion_matrix_router = APIRouter()


@get_confusion_matrix_router.get(
    "/evaluation/runs/{evaluation_run_id}/confusion-matrix",
    response_model=ConfusionMatrix,
)
def get_evaluation_confusion_matrix(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],  # noqa: ARG001
    evaluation_run_id: Annotated[UUID, Path(title="Evaluation Run ID")],
) -> ConfusionMatrix:
    """Get the confusion matrix for an evaluation run.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.
        evaluation_run_id: The evaluation run whose pairing metrics are aggregated.

    Returns:
        Confusion matrix with row/column labels and integer cell counts.

    Raises:
        HTTPException: 404 if the evaluation run was not found.
        HTTPException: 501 if the evaluation task type is not supported yet.
    """
    run = evaluation_run_resolver.get_by_id(
        session=session,
        evaluation_id=evaluation_run_id,
    )
    if run is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation run {evaluation_run_id} not found.",
        )
    if run.task_type in (
        EvaluationTaskType.OBJECT_DETECTION,
        EvaluationTaskType.CLASSIFICATION,
    ):
        return evaluation_annotation_metric_resolver.get_confusion_matrix(
            session=session,
            evaluation_run_id=evaluation_run_id,
        )
    raise HTTPException(
        status_code=HTTP_STATUS_NOT_IMPLEMENTED,
        detail=f"Evaluation task type '{run.task_type.value}' is not supported yet.",
    )
