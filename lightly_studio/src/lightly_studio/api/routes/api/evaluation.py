"""API routes for triggering and retrieving evaluation results."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_result import EvaluationResultView
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers import evaluation_result_resolver
from lightly_studio.services import evaluation_service

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluations"])


class EvaluationCreateInput(BaseModel):
    """Input for triggering a metric computation."""

    gt_collection_name: str
    prediction_collection_names: list[str]
    iou_threshold: float = 0.5
    confidence_threshold: float = 0.0


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
    """Compute COCO metrics and persist the result.

    Metrics are computed per prediction collection and per subset (one per tag + "all").
    """
    root_collection = session.exec(
        select(CollectionTable)
        .where(col(CollectionTable.dataset_id) == dataset_id)
        .where(col(CollectionTable.parent_collection_id).is_(None))
    ).first()
    if root_collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND, detail=f"Dataset {dataset_id} not found."
        )

    tags = list(
        session.exec(
            select(TagTable).where(col(TagTable.collection_id) == root_collection.collection_id)
        ).all()
    )

    try:
        result = evaluation_service.run_evaluation(
            session=session,
            dataset_id=dataset_id,
            gt_collection_name=body.gt_collection_name,
            prediction_collection_names=body.prediction_collection_names,
            tags=tags,
            iou_threshold=body.iou_threshold,
            confidence_threshold=body.confidence_threshold,
        )
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
    results = evaluation_result_resolver.get_all(session=session, dataset_id=dataset_id)
    return [EvaluationResultView.model_validate(r) for r in results]


@evaluation_router.get(
    "/evaluations/{evaluation_id}",
    response_model=EvaluationResultView,
)
def get_evaluation(
    dataset_id: Annotated[UUID, Path()],  # noqa: ARG001
    evaluation_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> EvaluationResultView:
    """Return a single evaluation result."""
    result = evaluation_result_resolver.get_by_id(session=session, evaluation_id=evaluation_id)
    if result is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Evaluation {evaluation_id} not found.",
        )
    return EvaluationResultView.model_validate(result)
