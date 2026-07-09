from __future__ import annotations

from collections.abc import Iterable
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
from tests.helpers_resolvers import create_annotation, create_collection


@dataclass
class AnnotationMetricStub:
    """Helper class to represent an annotation-level evaluation metric."""

    sample_id: UUID
    metric_name: str | None = None
    value: float | None = None
    pred_annotation_id: UUID | None = None
    gt_annotation_id: UUID | None = None


@dataclass
class TruePositiveMetricStub:
    """Helper class to create a true-positive annotation metric.

    Creates matching prediction and ground-truth annotations in the evaluation
    run's annotation collections, then stores metric rows that link both.
    """

    sample_id: UUID
    metrics: dict[str, float]
    gt_annotation_label_id: UUID
    # Prediction annotation label. If None, assumed to be equal to annotation_label_id.
    pred_annotation_label_id: UUID | None = None

    def metric_items(self) -> list[tuple[str, float]]:
        return list(self.metrics.items())

    def to_annotation_metric_stub(
        self, session: Session, run: EvaluationRunTable
    ) -> list[AnnotationMetricStub]:
        pred_collection = collection_resolver.get_by_id(
            session=session, collection_id=run.pred_annotation_collection_id
        )
        gt_collection = collection_resolver.get_by_id(
            session=session, collection_id=run.gt_annotation_collection_id
        )
        if pred_collection is None or gt_collection is None:
            raise ValueError(f"Evaluation run {run.id} references missing annotation collections")
        if (
            pred_collection.parent_collection_id is None
            or gt_collection.parent_collection_id is None
        ):
            raise ValueError(f"Evaluation run {run.id} annotation collections must have parents")

        # Note: `test_sample_filter.py` has the `_seed_pair()` helper function almost identical to
        # the following code block.
        pred_annotation = create_annotation(
            session=session,
            collection_id=pred_collection.parent_collection_id,
            sample_id=self.sample_id,
            annotation_label_id=self.pred_annotation_label_id or self.gt_annotation_label_id,
            annotation_collection_name=pred_collection.name,
        )
        gt_annotation = create_annotation(
            session=session,
            collection_id=gt_collection.parent_collection_id,
            sample_id=self.sample_id,
            annotation_label_id=self.gt_annotation_label_id,
            annotation_collection_name=gt_collection.name,
        )
        return [
            AnnotationMetricStub(
                sample_id=self.sample_id,
                metric_name=metric_name,
                value=value,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=gt_annotation.sample_id,
            )
            for metric_name, value in self.metric_items()
        ]


@dataclass
class FalsePositiveMetricStub:
    """Helper class to create a false-positive annotation metric.

    Creates a prediction annotation in the evaluation run's prediction collection,
    then stores metric rows that link the prediction with no ground truth.
    """

    sample_id: UUID
    pred_annotation_label_id: UUID
    metrics: dict[str, float] | None = None

    def metric_items(self) -> Iterable[tuple[str, float]]:
        return (self.metrics or {}).items()

    def to_annotation_metric_stub(
        self, session: Session, run: EvaluationRunTable
    ) -> list[AnnotationMetricStub]:
        pred_collection = collection_resolver.get_by_id(
            session=session, collection_id=run.pred_annotation_collection_id
        )
        if pred_collection is None:
            raise ValueError(
                f"Evaluation run {run.id} references missing prediction annotation collection"
            )
        if pred_collection.parent_collection_id is None:
            raise ValueError(
                f"Evaluation run {run.id} prediction annotation collection must have a parent"
            )

        pred_annotation = create_annotation(
            session=session,
            collection_id=pred_collection.parent_collection_id,
            sample_id=self.sample_id,
            annotation_label_id=self.pred_annotation_label_id,
            annotation_collection_name=pred_collection.name,
        )
        metrics = self.metric_items()
        if not metrics:
            return [
                AnnotationMetricStub(
                    sample_id=self.sample_id,
                    pred_annotation_id=pred_annotation.sample_id,
                    gt_annotation_id=None,
                )
            ]
        return [
            AnnotationMetricStub(
                sample_id=self.sample_id,
                metric_name=metric_name,
                value=value,
                pred_annotation_id=pred_annotation.sample_id,
                gt_annotation_id=None,
            )
            for metric_name, value in self.metric_items()
        ]


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
    pair_metric_stubs: list[TruePositiveMetricStub | FalsePositiveMetricStub] | None = None,
) -> list[AnnotationMetricStub]:
    annotation_metrics_to_create = list(annotation_metrics) if annotation_metrics else []
    pair_metric_stubs = pair_metric_stubs or []
    run = evaluation_run_resolver.get_by_id(session=session, evaluation_id=run_id)
    if run is None:
        raise ValueError(f"Evaluation run {run_id} doesn't exist")

    for stub in pair_metric_stubs:
        annotation_metrics_to_create.extend(
            stub.to_annotation_metric_stub(session=session, run=run)
        )

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
            for metric in annotation_metrics_to_create
        ],
    )
    return annotation_metrics_to_create
