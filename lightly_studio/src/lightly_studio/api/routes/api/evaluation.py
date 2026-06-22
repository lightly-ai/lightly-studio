"""API routes for evaluation runs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Union
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from lightly_studio.db_manager import SessionDep
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
    HTTP_STATUS_NOT_IMPLEMENTED,
)
from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    ImageDatasetEvaluate,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_run import EvaluationRunView, EvaluationTaskType
from lightly_studio.models.evaluation_sample_metric import EvaluationRunMetricsInfoView
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
    image_resolver,
)
from lightly_studio.resolvers.image_filter import ImageFilter

evaluation_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["evaluation"])


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


@evaluation_router.post(
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
    if collection.sample_type != SampleType.IMAGE:
        raise ValueError("Evaluation can only be triggered on image collections.")

    root_collection = collection_resolver.get_root_collection(
        session=session, collection_id=request.collection_id
    )
    sample_ids = image_resolver.get_sample_ids(
        session=session,
        collection_id=request.collection_id,
        filters=request.filter,
    )
    evaluator = ImageDatasetEvaluate(
        session=session,
        collection_id=root_collection.collection_id,
        sample_ids=sample_ids,
    )
    name = request.name or (
        f"{request.task_type.value} {datetime.now(timezone.utc):%Y-%m-%d %H:%M:%S}"
    )
    if isinstance(request, ObjectDetectionEvaluationRunCreateRequest):
        return evaluator.object_detection(
            name=name,
            gt_annotation_source=request.gt_annotation_source,
            pred_annotation_source=request.pred_annotation_source,
            config=request.config,
        )
    if isinstance(request, ClassificationEvaluationRunCreateRequest):
        return evaluator.classification(
            name=name,
            gt_annotation_source=request.gt_annotation_source,
            pred_annotation_source=request.pred_annotation_source,
            config=request.config,
        )
    return evaluator.semantic_segmentation(
        name=name,
        gt_annotation_source=request.gt_annotation_source,
        pred_annotation_source=request.pred_annotation_source,
        config=request.config,
    )


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
