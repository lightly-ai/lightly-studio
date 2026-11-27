"""Evaluation of an image dataset query through the active transport."""

from __future__ import annotations

from collections.abc import Callable
from uuid import UUID

from sqlmodel import Session
from typing_extensions import override  # typing.override needs Python 3.12.

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.evaluation.image_dataset_evaluate import ImageDatasetEvaluate
from lightly_studio.models.evaluation_run import EvaluationTaskType
from lightly_studio.models.evaluation_task import (
    EvaluationResult,
    EvaluationTask,
    ObjectDetectionEvaluationConfig,
)
from lightly_studio.transport import active_transport


class TransportImageDatasetEvaluate(ImageDatasetEvaluate):
    """Evaluates the samples of a query through the active transport.

    A query that the transport cannot send, or that has its own session, is evaluated with the
    database session.
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
        task = EvaluationTask(
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            config=config or ObjectDetectionEvaluationConfig(),
        )
        return self._evaluate(task=task, evaluate_locally=super().object_detection)

    def _evaluate(
        self, task: EvaluationTask, evaluate_locally: Callable[..., EvaluationResult]
    ) -> EvaluationResult:
        """Evaluate through the transport, or with SQL if the transport cannot send the query.

        Raises:
            UnsupportedQueryError: If the transport is remote and cannot send the query.
        """
        request = self._query._evaluation_request()  # noqa: SLF001
        # The transport cannot use the session of the query.
        has_own_session = self._query._session is not None  # noqa: SLF001
        if request is None or has_own_session:
            return evaluate_locally(
                name=task.name,
                gt_annotation_source=task.gt_annotation_source,
                pred_annotation_source=task.pred_annotation_source,
                config=task.config,
            )
        return active_transport.get_transport().compute.evaluate(
            collection_id=self._query.dataset.collection_id,
            query_expr=request.query_expr,
            task=task,
        )
