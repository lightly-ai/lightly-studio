"""API routes for training models with LightlyTrain."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from lightly_studio.api.dependencies.identity import Identity, Role, require_role
from lightly_studio.api.routes.api import collection as collection_api
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.dataset import env
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.training_run import TrainingRunCreate, TrainingRunView
from lightly_studio.services.training_service import (
    cancel_training_run,
    start_training_run,
    training_run_view,
)
from lightly_studio.services.training_service.training_run_registry import training_run_registry

training_router = APIRouter(prefix="/collections/{collection_id}/training", tags=["training"])

CollectionDep = Annotated[
    CollectionTable,
    Path(title="collection Id"),
    Depends(collection_api.get_and_validate_collection_id),
]
EditorDep = Annotated[Identity, Depends(require_role(min_role=Role.EDITOR))]


@training_router.post("/runs")
def create_training_run(
    collection: CollectionDep,
    session: SessionDep,
    body: TrainingRunCreate,
    _identity: EditorDep,
) -> TrainingRunView:
    """Start a training run. The request returns when the training process has started."""
    if collection.sample_type != SampleType.IMAGE:
        raise ValueError("Training is only supported for image collections.")
    run = start_training_run.start_training_run(
        session=session,
        collection=collection,
        run_create=body,
        registry=training_run_registry,
        runs_dir=env.LIGHTLY_STUDIO_TRAINING_RUNS_DIR,
    )
    return training_run_view.to_view(run=run)


@training_router.get("/runs")
def get_training_runs(collection: CollectionDep) -> list[TrainingRunView]:
    """Get the training runs of the collection, newest first."""
    runs = training_run_registry.list_for_collection(collection_id=collection.collection_id)
    return [training_run_view.to_view(run=run) for run in runs]


@training_router.post("/runs/{training_run_id}/cancel")
def cancel_training_run_by_id(
    collection: CollectionDep,
    training_run_id: UUID,
    _identity: EditorDep,
) -> TrainingRunView:
    """Stop the training process of a run."""
    run = cancel_training_run.cancel_training_run(
        registry=training_run_registry,
        collection_id=collection.collection_id,
        training_run_id=training_run_id,
    )
    return training_run_view.to_view(run=run)
