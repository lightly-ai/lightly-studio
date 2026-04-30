"""API routes for triggering and retrieving evaluation results."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.evaluation import run_evaluation
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_result import EvaluationResultView, EvaluationTaskType
from lightly_studio.resolvers import evaluation_result_resolver

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluations"])


class EvaluationCreateInput(BaseModel):
    """Request body for POST /evaluations."""

    name: str
    gt_collection_name: str
    prediction_collection_name: str
    task_type: EvaluationTaskType = EvaluationTaskType.OBJECT_DETECTION
    iou_threshold: float = 0.5
    confidence_threshold: float = 0.0
    sample_ids: list[UUID] | None = None


class SampleCountsResponse(BaseModel):
    """Per-image TP/FP/FN count map returned by the sample-counts endpoint."""

    counts: dict[str, dict[str, int]]


def _get_root_collection_or_404(
    session: SessionDep,
    root_collection_id: UUID,
) -> CollectionTable:
    """Resolve the route-level dataset identifier to the root collection row.

    In the GUI routes, ``/datasets/{dataset_id}`` historically carries the root
    collection UUID, not the dataset table UUID.
    """
    root_collection = session.get(CollectionTable, root_collection_id)
    if root_collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Dataset {root_collection_id} not found.",
        )
    return root_collection


@evaluation_router.post(
    "/evaluations",
    response_model=EvaluationResultView,
    status_code=201,
)
def create_evaluation(
    dataset_id: Annotated[UUID, Path()],
    session: SessionDep,
    body: EvaluationCreateInput,
) -> EvaluationResultView:
    """Compute one evaluation run and persist the result."""
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)
    if body.sample_ids is None:
        sample_ids = DatasetQuery(dataset=root_collection, session=session).get_sample_ids()
    else:
        sample_ids = body.sample_ids

    try:
        result = run_evaluation(
            session=session,
            dataset_id=root_collection.dataset_id,
            name=body.name,
            gt_collection_name=body.gt_collection_name,
            prediction_collection_name=body.prediction_collection_name,
            sample_ids=sample_ids,
            task_type=body.task_type,
            iou_threshold=body.iou_threshold,
            confidence_threshold=body.confidence_threshold,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=str(exc)) from exc

    return EvaluationResultView.model_validate(result)


@evaluation_router.get(
    "/evaluations",
    response_model=list[EvaluationResultView],
)
def list_evaluations(
    dataset_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> list[EvaluationResultView]:
    """Return all evaluation results for a dataset, newest first."""
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)
    results = evaluation_result_resolver.get_all(
        session=session, dataset_id=root_collection.dataset_id
    )
    return [EvaluationResultView.model_validate(r) for r in results]


@evaluation_router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResultView,
)
def get_evaluation(
    dataset_id: Annotated[UUID, Path()],
    evaluation_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> EvaluationResultView:
    """Return a single evaluation result."""
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)
    result = evaluation_result_resolver.get_by_id(session=session, evaluation_id=evaluation_id)
    if result is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found.",
        )
    if result.dataset_id != root_collection.dataset_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found.",
        )
    return EvaluationResultView.model_validate(result)


@evaluation_router.get(
    "/evaluations/{evaluation_id}/sample-counts",
    response_model=SampleCountsResponse,
)
def get_evaluation_sample_counts(
    dataset_id: Annotated[UUID, Path()],
    evaluation_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> SampleCountsResponse:
    """Return per-image TP/FP/FN counts for an evaluation run."""
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)
    result = evaluation_result_resolver.get_by_id(session=session, evaluation_id=evaluation_id)
    if result is None or result.dataset_id != root_collection.dataset_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found.",
        )
    counts = evaluation_result_resolver.get_sample_counts(
        session=session, evaluation_result_id=evaluation_id
    )
    return SampleCountsResponse(counts={str(k): v for k, v in counts.items()})
