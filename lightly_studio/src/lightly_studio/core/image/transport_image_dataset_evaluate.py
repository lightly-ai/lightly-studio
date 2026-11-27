"""Evaluation of an image dataset query through the active transport."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlmodel import Session
from typing_extensions import override  # typing.override needs Python 3.12.

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.evaluation.image_dataset_evaluate import ImageDatasetEvaluate
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import EvaluationRunView, EvaluationTaskType
from lightly_studio.models.evaluation_task import (
    ClassificationEvaluationConfig,
    EvaluationConfig,
    EvaluationResult,
    EvaluationTask,
    InstanceSegmentationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.transport import active_transport


class TransportImageDatasetEvaluate(ImageDatasetEvaluate):
    """Evaluates the samples of a query through the active transport.

    A query that the transport cannot send, or that has its own session, is evaluated with the
    database session. The runs, confusion matrices and metrics are always read through the
    transport.
    """

    def __init__(self, session: Session, collection_id: UUID, query: DatasetQuery) -> None:
        """Create the evaluation of the samples of a query."""
        super().__init__(
            session=session,
            collection_id=collection_id,
            # A generator, so the dataset scan runs only when the SQL path reads sample_ids.
            sample_ids=(sample.sample_id for sample in query),
        )
        self._query = query

    @override
    def object_detection(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: ObjectDetectionEvaluationConfig | None = None,
    ) -> EvaluationResult:
        return self._evaluate(
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config or ObjectDetectionEvaluationConfig(),
        )

    @override
    def classification(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: ClassificationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        return self._evaluate(
            task_type=EvaluationTaskType.CLASSIFICATION,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config or ClassificationEvaluationConfig(),
        )

    @override
    def semantic_segmentation(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: SemanticSegmentationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        return self._evaluate(
            task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config or SemanticSegmentationEvaluationConfig(),
        )

    @override
    def instance_segmentation(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: InstanceSegmentationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        return self._evaluate(
            task_type=EvaluationTaskType.INSTANCE_SEGMENTATION,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config or InstanceSegmentationEvaluationConfig(),
        )

    @override
    def list_runs(self) -> list[EvaluationRunView]:
        return active_transport.get_transport().compute.list_evaluation_runs(
            collection_id=self.collection_id
        )

    @override
    def confusion_matrix(self, run_id: UUID) -> ConfusionMatrix:
        return active_transport.get_transport().compute.get_evaluation_confusion_matrix(
            collection_id=self.collection_id, run_id=run_id
        )

    @override
    def metrics(self, run_id: UUID) -> EvaluationMetrics:
        return active_transport.get_transport().compute.get_evaluation_metrics(
            collection_id=self.collection_id, run_id=run_id
        )

    def _evaluate(
        self,
        task_type: EvaluationTaskType,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: EvaluationConfig,
    ) -> EvaluationResult:
        """Evaluate through the transport, or with SQL if the transport cannot send the query.

        Raises:
            UnsupportedQueryError: If the transport is remote and cannot send the query.
        """
        request = self._query._evaluation_request()  # noqa: SLF001
        # The transport cannot use the session of the query.
        has_own_session = self._query._session is not None  # noqa: SLF001
        if request is None or has_own_session:
            # Each task method of the base class has the name of its task type.
            evaluate_locally: Callable[..., EvaluationResult] = getattr(super(), task_type.value)
            return evaluate_locally(
                name=name,
                gt_annotation_source=gt_annotation_source,
                pred_annotation_source=pred_annotation_source,
                config=config,
            )
        task = EvaluationTask(
            task_type=task_type,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config,
        )
        return active_transport.get_transport().compute.evaluate(
            collection_id=self._query.dataset.collection_id,
            query_expr=request.query_expr,
            task=task,
        )
