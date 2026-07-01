from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_annotation_metric import EvaluationAnnotationMetricCreate
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from tests.helpers_resolvers import create_collection


@dataclass
class AnnotationMetricStub:
    """Helper class to represent an annotation-level evaluation metric."""

    sample_id: UUID
    metric_name: str
    value: float
    pred_annotation_id: UUID | None = None
    gt_annotation_id: UUID | None = None


@dataclass
class SampleMetricStub:
    """Helper class to represent a sample-level evaluation metric."""

    sample_id: UUID
    metrics: dict[str, float]


def create_run(
    session: Session,
    collection_id: UUID | None = None,
    name: str = "test_run",
) -> EvaluationRunTable:
    """Create an evaluation run with ground truth/prediction annotation collections."""
    if collection_id is not None:
        collection = collection_resolver.get_by_id(
            session=session,
            collection_id=collection_id,
        )
        if collection is None:
            raise RuntimeError(f"Collection {collection_id} doesn't exist")
    else:
        collection = create_collection(session=session)
        collection_id = collection.collection_id

    gt_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection_id,
    )
    pred_collection = create_collection(
        session=session,
        sample_type=SampleType.ANNOTATION,
        parent_collection_id=collection_id,
    )
    return evaluation_run_resolver.create(
        session=session,
        evaluation_run_input=EvaluationRunCreate(
            name=name,
            dataset_id=collection.dataset_id,
            gt_annotation_collection_id=gt_collection.collection_id,
            pred_annotation_collection_id=pred_collection.collection_id,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        ),
    )


def create_sample_metrics(
    session: Session,
    run_id: UUID,
    sample_metrics: list[SampleMetricStub] | None = None,
) -> None:
    sample_metrics = sample_metrics or []
    evaluation_sample_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationSampleMetricCreate(
                evaluation_run_id=run_id,
                sample_id=stub.sample_id,
                metric_name=metric,
                value=value,
            )
            for stub in sample_metrics
            for metric, value in stub.metrics.items()
        ],
    )


def create_annotation_metrics(
    session: Session,
    run_id: UUID,
    annotation_metrics: list[AnnotationMetricStub] | None = None,
) -> None:
    annotation_metrics = annotation_metrics or []
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None:
        raise ValueError(f"Evaluation run {run_id} doesn't exist")

    evaluation_annotation_metric_resolver.create_many(
        session=session,
        records=[
            EvaluationAnnotationMetricCreate(
                evaluation_run_id=run_id,
                sample_id=metric.sample_id,
                pred_annotation_id=metric.pred_annotation_id,
                gt_annotation_id=metric.gt_annotation_id,
                metric_name=metric.metric_name,
                value=metric.value,
            )
            for metric in annotation_metrics
        ],
    )
