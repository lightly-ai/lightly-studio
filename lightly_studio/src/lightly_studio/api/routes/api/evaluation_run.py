"""API routes for evaluation runs and confusion matrix."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.evaluation_annotation_match import ConfusionMatrixCell
from lightly_studio.models.evaluation_run import EvaluationRunTable
from lightly_studio.resolvers import evaluation_annotation_match_resolver, evaluation_run_resolver

evaluation_run_router = APIRouter(tags=["evaluation_run"])


class EvaluationRunView(BaseModel):
    """Serialisable view of one evaluation run."""

    id: UUID
    name: str
    task_type: str
    gt_annotation_collection_id: UUID
    pred_annotation_collection_id: UUID
    gt_collection_name: str
    pred_collection_name: str
    config_json: dict[str, Any]
    created_at: str


class ConfusionMatrixLabelView(BaseModel):
    """Label id + name pair used in the confusion matrix response."""

    label_id: UUID
    label_name: str


class ConfusionMatrixResponse(BaseModel):
    """Full confusion matrix with label metadata."""

    cells: list[ConfusionMatrixCell]
    labels: list[ConfusionMatrixLabelView]


def _collection_name(session: Session, collection_id: UUID) -> str:
    col_row = session.get(CollectionTable, collection_id)
    return col_row.name if col_row else str(collection_id)


def _to_view(session: Session, run: EvaluationRunTable) -> EvaluationRunView:
    return EvaluationRunView(
        id=run.id,
        name=run.name,
        task_type=run.task_type,
        gt_annotation_collection_id=run.gt_annotation_collection_id,
        pred_annotation_collection_id=run.pred_annotation_collection_id,
        gt_collection_name=_collection_name(session, run.gt_annotation_collection_id),
        pred_collection_name=_collection_name(session, run.pred_annotation_collection_id),
        config_json=run.config_json,
        created_at=str(run.created_at),
    )


@evaluation_run_router.get("/datasets/{dataset_id}/evaluation_runs")
def list_evaluation_runs(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
) -> list[EvaluationRunView]:
    """Return all evaluation runs for a dataset, newest first.

    The dataset_id path parameter is the root collection_id used in GUI URLs.
    We resolve it to the actual DatasetTable.dataset_id via the collection lookup.
    """
    collection = session.get(CollectionTable, dataset_id)
    if collection is None:
        return []
    runs = evaluation_run_resolver.get_all_by_dataset_id(
        session=session, dataset_id=collection.dataset_id
    )
    return [_to_view(session, r) for r in runs]


@evaluation_run_router.get("/evaluation_runs/{run_id}")
def get_evaluation_run(
    session: SessionDep,
    run_id: Annotated[UUID, Path(title="Evaluation Run Id")],
) -> EvaluationRunView:
    """Return a single evaluation run by ID."""
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Evaluation run not found")
    return _to_view(session, run)


@evaluation_run_router.get("/evaluation_runs/{run_id}/confusion_matrix")
def get_confusion_matrix(
    session: SessionDep,
    run_id: Annotated[UUID, Path(title="Evaluation Run Id")],
) -> ConfusionMatrixResponse:
    """Return the NxN confusion matrix for an evaluation run."""
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Evaluation run not found")

    cells = evaluation_annotation_match_resolver.get_confusion_matrix(
        session=session, evaluation_run_id=run_id
    )

    # Collect unique label IDs referenced in the matrix.
    label_ids: set[UUID] = set()
    for cell in cells:
        if cell.gt_label_id:
            label_ids.add(cell.gt_label_id)
        if cell.pred_label_id:
            label_ids.add(cell.pred_label_id)

    labels: list[ConfusionMatrixLabelView] = []
    if label_ids:
        stmt = select(AnnotationLabelTable).where(
            col(AnnotationLabelTable.annotation_label_id).in_(label_ids)
        )
        for label in session.exec(stmt).all():
            labels.append(
                ConfusionMatrixLabelView(
                    label_id=label.annotation_label_id,
                    label_name=label.annotation_label_name,
                )
            )

    return ConfusionMatrixResponse(cells=cells, labels=labels)
