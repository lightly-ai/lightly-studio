"""API routes for evaluation runs."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND, HTTP_STATUS_NOT_IMPLEMENTED
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_run import EvaluationRunView, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationRunMetricsInfoView
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)

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
            gt_annotation_source=collection_name_by_id[run.gt_annotation_collection_id],
            pred_annotation_source=collection_name_by_id[run.pred_annotation_collection_id],
        )
        for run in runs
    ]


@evaluation_router.get(
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
