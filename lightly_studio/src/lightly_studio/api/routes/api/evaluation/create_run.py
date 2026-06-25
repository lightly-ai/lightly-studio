"""Route to trigger a new evaluation run."""

from __future__ import annotations

from typing import Annotated, Literal, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.services import evaluation_service

create_run_router = APIRouter()


class _EvaluationRunCreateRequestBase(BaseModel):
    """Fields shared by all evaluation run trigger requests."""

    gt_annotation_source: str = Field(
        min_length=1, description="Name of the annotation source with ground truth annotations"
    )
    pred_annotation_source: str = Field(
        min_length=1, description="Name of the annotation source with predictions"
    )
    collection_id: UUID = Field(description="Collection of the active view to evaluate on")
    filter: ImageFilter | None = Field(
        default=None, description="Filter of the active view; evaluates all samples if omitted"
    )
    name: str | None = Field(
        default=None, description="Display name of the run; auto-generated if omitted"
    )


class ObjectDetectionEvaluationRunCreateRequest(_EvaluationRunCreateRequestBase):
    """Request model for triggering an object-detection evaluation run."""

    task_type: Literal[EvaluationTaskType.OBJECT_DETECTION]
    config: ObjectDetectionEvaluationConfig = Field(default_factory=ObjectDetectionEvaluationConfig)


class ClassificationEvaluationRunCreateRequest(_EvaluationRunCreateRequestBase):
    """Request model for triggering a classification evaluation run."""

    task_type: Literal[EvaluationTaskType.CLASSIFICATION]
    config: ClassificationEvaluationConfig = Field(default_factory=ClassificationEvaluationConfig)


class SemanticSegmentationEvaluationRunCreateRequest(_EvaluationRunCreateRequestBase):
    """Request model for triggering a semantic-segmentation evaluation run."""

    task_type: Literal[EvaluationTaskType.SEMANTIC_SEGMENTATION]
    config: SemanticSegmentationEvaluationConfig = Field(
        default_factory=SemanticSegmentationEvaluationConfig
    )


EvaluationRunCreateRequest = Annotated[
    Union[
        ObjectDetectionEvaluationRunCreateRequest,
        ClassificationEvaluationRunCreateRequest,
        SemanticSegmentationEvaluationRunCreateRequest,
    ],
    Field(discriminator="task_type"),
]


@create_run_router.post(
    "/evaluation/runs",
    response_model=EvaluationResult,
    status_code=HTTP_STATUS_CREATED,
)
def create_evaluation_run(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset ID")],
    request: EvaluationRunCreateRequest,
) -> EvaluationResult:
    """Trigger a new evaluation run on the current active view.

    The evaluation executes synchronously; the request blocks until the run
    has completed.

    Args:
        session: The database session.
        dataset_id: The dataset's UUID.
        request: Task type, annotation sources, task-specific config, and the
            active view context (collection and filter) to evaluate on.

    Returns:
        Summary of the created run, including its ID and input counts.

    Raises:
        HTTPException: 404 if the collection was not found or does not belong
            to the dataset.
        ValueError: If the collection is not an image collection, the same
            annotation source is used for ground truth and predictions, or an
            annotation source is missing or has the wrong annotation type.
            Mapped to a 400 response by the global exception handler.
    """
    collection = collection_resolver.get_by_id(session=session, collection_id=request.collection_id)
    if collection is None or collection.dataset_id != dataset_id:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection {request.collection_id} not found in dataset {dataset_id}.",
        )
    return evaluation_service.run_evaluation(
        session=session,
        collection=collection,
        task_type=request.task_type,
        gt_annotation_source=request.gt_annotation_source,
        pred_annotation_source=request.pred_annotation_source,
        config=request.config,
        filters=request.filter,
        name=request.name,
    )
