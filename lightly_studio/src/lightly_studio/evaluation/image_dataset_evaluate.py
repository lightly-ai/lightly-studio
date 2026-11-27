"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from functools import cached_property
from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.evaluation import (
    aggregate_metrics,
    average_precision,
    classification_metric,
    evaluation_data,
    instance_segmentation_metric,
    semantic_segmentation_metric,
    validators,
)
from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_confusion_matrix import ConfusionMatrix
from lightly_studio.models.evaluation_metrics import EvaluationMetrics
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationRunView,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_task import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    InstanceSegmentationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    evaluation_annotation_metric_resolver,
    evaluation_class_metric_resolver,
    evaluation_run_resolver,
)

__all__ = [
    "ClassificationEvaluationConfig",
    "EvaluationResult",
    "ImageDatasetEvaluate",
    "InstanceSegmentationEvaluationConfig",
    "ObjectDetectionEvaluationConfig",
    "SemanticSegmentationEvaluationConfig",
]


class ImageDatasetEvaluate:
    """Task-specific evaluation entry points for image datasets.

    This facade groups evaluation methods by task (e.g. object detection)
    and keeps evaluation-specific logic separate from ``ImageDataset``.
    """

    def __init__(self, session: Session, collection_id: UUID, sample_ids: Iterable[UUID]) -> None:
        """Initialize the evaluator facade.

        Args:
            session: Database session used by resolver calls.
            collection_id: ID of the collection being evaluated.
            sample_ids: IDs of the samples selected for evaluation.
        """
        self.session = session
        self.collection_id = collection_id
        self._sample_ids_source: Iterable[UUID] = sample_ids

    @cached_property
    def sample_ids(self) -> set[UUID]:
        """The IDs of the samples selected for evaluation, materialized once on first read."""
        # Materialize once: callers may pass a single-use generator, and the
        # facade can be reused across task methods (object_detection(),
        # classification(), ...). Without this, the second call would see an
        # exhausted iterator and silently evaluate zero samples. Deferred to the first
        # read so readback methods (list_runs(), confusion_matrix()) do not scan.
        return set(self._sample_ids_source)

    def object_detection(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: ObjectDetectionEvaluationConfig | None = None,
    ) -> EvaluationResult:
        """Create an object-detection evaluation run and persist per-image metrics.

        Args:
            name: Display name of the evaluation run.
            gt_annotation_source: Name of the annotation source containing ground truth annotations.
            pred_annotation_source: Name of the annotation source containing predictions.
            config: Optional object-detection evaluation config. If omitted,
                defaults are used.

        Returns:
            Summary of the samples and annotations used by the evaluation.
        """
        config = config or ObjectDetectionEvaluationConfig()
        data = self._prepare_evaluation_data(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            config_json=config.model_dump(),
        )
        average_precision.create_and_persist_object_detection_metrics(
            session=self.session,
            data=data,
            iou_threshold=config.iou_threshold,
            classwise=config.classwise,
            compute_average_precision=config.compute_average_precision,
        )
        return evaluation_data.to_evaluation_result(data=data)

    def classification(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: ClassificationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        """Create a classification evaluation run and persist per-image metrics.

        Args:
            name: Display name of the evaluation run.
            gt_annotation_source: Name of the annotation source containing ground truth annotations.
            pred_annotation_source: Name of the annotation source containing predictions.
            config: Optional classification evaluation config. If omitted,
                defaults are used.

        Returns:
            Summary of the samples and annotations used by the evaluation.
        """
        config = config or ClassificationEvaluationConfig()
        data = self._prepare_evaluation_data(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=EvaluationTaskType.CLASSIFICATION,
            config_json=config.model_dump(),
        )
        classification_metric.create_and_persist_classification_metrics_per_sample(
            session=self.session,
            data=data,
        )
        return evaluation_data.to_evaluation_result(data=data)

    def semantic_segmentation(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: SemanticSegmentationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        """Create a semantic segmentation evaluation run and persist per-image metrics.

        Args:
            name: Display name of the evaluation run.
            gt_annotation_source: Name of the annotation source containing ground truth labels.
            pred_annotation_source: Name of the annotation source containing predictions.
            config: Optional semantic segmentation evaluation config. If omitted,
                defaults are used.

        Returns:
            Summary of the samples and annotations used by the evaluation.
        """
        config = config or SemanticSegmentationEvaluationConfig()
        data = self._prepare_evaluation_data(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=EvaluationTaskType.SEMANTIC_SEGMENTATION,
            config_json=config.model_dump(),
        )
        semantic_segmentation_metric.create_and_persist_semantic_segmentation_metrics_per_sample(
            session=self.session,
            data=data,
        )
        return evaluation_data.to_evaluation_result(data=data)

    def instance_segmentation(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        config: InstanceSegmentationEvaluationConfig | None = None,
    ) -> EvaluationResult:
        """Create an instance-segmentation evaluation run and persist per-image metrics.

        Args:
            name: Display name of the evaluation run.
            gt_annotation_source: Name of the annotation source containing ground truth masks.
            pred_annotation_source: Name of the annotation source containing predictions.
            config: Optional instance segmentation evaluation config. If omitted,
                defaults are used.

        Returns:
            Summary of the samples and annotations used by the evaluation.
        """
        config = config or InstanceSegmentationEvaluationConfig()
        data = self._prepare_evaluation_data(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=EvaluationTaskType.INSTANCE_SEGMENTATION,
            config_json=config.model_dump(),
        )
        instance_segmentation_metric.create_and_persist_instance_segmentation_metrics_per_sample(
            session=self.session,
            data=data,
            iou_threshold=config.iou_threshold,
            classwise=config.classwise,
        )
        return evaluation_data.to_evaluation_result(data=data)

    def list_runs(self) -> list[EvaluationRunView]:
        """List the evaluation runs stored for this dataset, newest first.

        Returns:
            A view per run, with its id, name, configuration, creation time, and
            resolved ground-truth and prediction source names.
        """
        return evaluation_run_resolver.list_views_by_dataset_id(
            session=self.session,
            dataset_id=self._dataset_id(),
        )

    def confusion_matrix(self, run_id: UUID) -> ConfusionMatrix:
        """Return the confusion matrix of an evaluation run.

        The matrix aggregates the run's persisted ground-truth/prediction
        annotation pairings by label. Object detection, classification, and
        instance segmentation are supported; semantic segmentation does not
        produce a confusion matrix.

        Args:
            run_id: ID of the evaluation run.

        Returns:
            The confusion matrix, with a shared class axis and synthetic
            false-positive and false-negative axes.

        Raises:
            ValueError: If no run with ``run_id`` exists in this dataset.
            NotImplementedError: If the run's task type has no confusion matrix.
        """
        _, matrix = self._confusion_matrix_with_run(run_id)
        return matrix

    def metrics(self, run_id: UUID) -> EvaluationMetrics:
        """Return aggregate metrics for an evaluation run.

        Derives per-class and micro-averaged precision, recall, and F1 from the
        run's confusion matrix, plus accuracy for classification runs. For
        object-detection runs created with ``compute_average_precision=True`` it also
        includes the per-class and mean average precision. Object detection and
        classification are supported; segmentation tasks have no confusion matrix and
        so no confusion-derived metrics.

        Args:
            run_id: ID of the evaluation run.

        Returns:
            The aggregate metrics for the run.

        Raises:
            ValueError: If no run with ``run_id`` exists in this dataset.
            NotImplementedError: If the run's task type has no confusion matrix.
        """
        run, matrix = self._confusion_matrix_with_run(run_id)
        metrics = aggregate_metrics.compute_aggregate_metrics_from_confusion_matrix(
            matrix=matrix,
            task_type=run.task_type,
        )
        if run.task_type != EvaluationTaskType.OBJECT_DETECTION:
            return metrics
        by_label = average_precision.by_label_and_threshold(
            class_metrics=evaluation_class_metric_resolver.get_all_by_evaluation_run_id(
                session=self.session, evaluation_run_id=run.id
            ),
            run_config=run.config_json,
        )
        # Resolve names at read time, so renamed labels keep their values and deleted
        # labels are skipped.
        labels = annotation_label_resolver.get_by_ids(session=self.session, ids=list(by_label))
        return average_precision.with_average_precision(
            metrics=metrics,
            by_class={
                label.annotation_label_name: by_label[label.annotation_label_id] for label in labels
            },
        )

    def _confusion_matrix_with_run(
        self, run_id: UUID
    ) -> tuple[EvaluationRunTable, ConfusionMatrix]:
        """Fetch a run and its confusion matrix, validating the run and its task type.

        Raises:
            ValueError: If no run with ``run_id`` exists in this dataset.
            NotImplementedError: If the run's task type has no confusion matrix.
        """
        run = evaluation_run_resolver.get_by_id(session=self.session, evaluation_id=run_id)
        if run is None or run.dataset_id != self._dataset_id():
            raise ValueError(f"Evaluation run {run_id} not found in this dataset.")
        if not evaluation_annotation_metric_resolver.supports_confusion_matrix(run.task_type):
            raise NotImplementedError(
                f"Evaluation task type {run.task_type.value!r} has no confusion matrix."
            )
        matrix = evaluation_annotation_metric_resolver.get_confusion_matrix(
            session=self.session,
            evaluation_run_id=run_id,
        )
        return run, matrix

    def _dataset_id(self) -> UUID:
        """Resolve the dataset ID of the evaluated collection."""
        collection = collection_resolver.get_by_id(
            session=self.session, collection_id=self.collection_id
        )
        if collection is None:
            raise ValueError(f"Collection {self.collection_id} not found.")
        return collection.dataset_id

    def _prepare_evaluation_data(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        task_type: EvaluationTaskType,
        config_json: dict[str, Any],
    ) -> EvaluationData:
        """Create the EvaluationRun, intersect sample coverage, fetch and group annotations.

        Shared across task methods; each per-task wrapper delegates to this helper
        and then calls its task-specific metric module with the returned data.
        """
        annotation_type = validators.get_annotation_type_for_task(task_type)
        selected_sample_ids = set(self.sample_ids)
        gt_collection_id, pred_collection_id, evaluation_run = self._create_evaluation_run(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=task_type,
            config_json=config_json,
        )

        gt_covered_sample_ids = set(
            annotation_collection_coverage_resolver.list_by_collection_id(
                session=self.session,
                annotation_collection_id=gt_collection_id,
            )
        )
        pred_covered_sample_ids = set(
            annotation_collection_coverage_resolver.list_by_collection_id(
                session=self.session,
                annotation_collection_id=pred_collection_id,
            )
        )
        selected_sample_ids &= gt_covered_sample_ids & pred_covered_sample_ids
        # TODO(Horatiu, 05/2026): if the number of annotations per sample is large, we may want
        # to avoid loading them all into memory at once and instead stream them in batches.
        gt_annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
            session=self.session,
            parent_sample_ids=list(selected_sample_ids),
            annotation_collection_id=gt_collection_id,
            annotation_type=annotation_type,
        )
        pred_annotations = annotation_resolver.get_all_by_collection_id_and_parent_sample_ids(
            session=self.session,
            parent_sample_ids=list(selected_sample_ids),
            annotation_collection_id=pred_collection_id,
            annotation_type=annotation_type,
        )
        return EvaluationData(
            evaluation_run_id=evaluation_run.id,
            selected_sample_ids=selected_sample_ids,
            gt_per_sample=self._group_by_parent_sample_id(annotations=gt_annotations),
            pred_per_sample=self._group_by_parent_sample_id(annotations=pred_annotations),
        )

    def _create_evaluation_run(
        self,
        name: str,
        gt_annotation_source: str,
        pred_annotation_source: str,
        task_type: EvaluationTaskType,
        config_json: dict[str, Any],
    ) -> tuple[UUID, UUID, EvaluationRunTable]:
        """Validate gt + pred collections and persist the evaluation run.

        Args:
            name: Display name of the evaluation run.
            gt_annotation_source: Name of the annotation source containing
                ground truth annotations.
            pred_annotation_source: Name of the annotation source containing
                predictions.
            task_type: Evaluation task type; determines the expected annotation type
                for both collections and is stored on the run.
            config_json: Task-specific configuration to persist on the run.

        Returns:
            Tuple of (gt_collection_id, pred_collection_id, evaluation_run).

        Raises:
            ValueError: If the same annotation source is used for both ground
                truth and predictions.
        """
        if gt_annotation_source == pred_annotation_source:
            raise ValueError(
                "Ground truth and prediction annotation sources must be different, "
                f"got {gt_annotation_source!r} for both."
            )
        gt_collection_id = validators.resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=gt_annotation_source,
            task_type=task_type,
        )
        pred_collection_id = validators.resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=pred_annotation_source,
            task_type=task_type,
        )
        evaluation_run = evaluation_run_resolver.create(
            session=self.session,
            evaluation_run_input=EvaluationRunCreate(
                name=name,
                gt_annotation_collection_id=gt_collection_id,
                pred_annotation_collection_id=pred_collection_id,
                dataset_id=self._dataset_id(),
                task_type=task_type,
                config_json=config_json,
            ),
        )
        return gt_collection_id, pred_collection_id, evaluation_run

    @staticmethod
    def _group_by_parent_sample_id(
        annotations: Sequence[AnnotationBaseTable],
    ) -> dict[UUID, list[AnnotationBaseTable]]:
        """Group annotation rows by their parent image sample id."""
        grouped: dict[UUID, list[AnnotationBaseTable]] = {}
        for annotation in annotations:
            grouped.setdefault(annotation.parent_sample_id, []).append(annotation)
        return grouped
