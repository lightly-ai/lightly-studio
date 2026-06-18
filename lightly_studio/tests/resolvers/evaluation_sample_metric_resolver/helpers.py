from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers import (
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection, create_image


def create_run_and_image(
    session: Session,
    dataset_collection_id: UUID | None = None,
    name: str = "test_run",
) -> tuple[EvaluationRunTable, ImageTable]:
    if dataset_collection_id is None:
        dataset_collection_id = create_collection(session=session).collection_id
    gt_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=dataset_collection_id,
    )
    run = evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name=name,
            gt_annotation_collection_id=gt_collection.collection_id,
            dataset_id=gt_collection.dataset_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )
    image = create_image(session=session, collection_id=dataset_collection_id)
    return run, image


def create_evaluation_metrics(
    session: Session,
    run_id: UUID,
    pred_annotation: AnnotationBaseTable,
    gt_annotation: AnnotationBaseTable,
) -> None:
    evaluation_annotation_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=pred_annotation.parent_sample_id,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
                metric_name="iou",
                value=0.75,
            )
        ],
    )
    evaluation_sample_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run_id,
                sample_id=pred_annotation.parent_sample_id,
                metric_name="score",
                value=0.5,
            )
        ],
    )


def insert_metrics(
    session: Session,
    evaluation_run_id: UUID,
    sample_id: UUID,
    metrics: dict[str, float],
) -> None:
    evaluation_sample_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=evaluation_run_id,
                sample_id=sample_id,
                metric_name=name,
                value=value,
            )
            for name, value in metrics.items()
        ],
    )
