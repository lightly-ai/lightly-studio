"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.evaluation import classification_metric, object_detection_metric, validators
from lightly_studio.evaluation.evaluation_data import EvaluationData
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunTable,
    EvaluationTaskType,
)
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    evaluation_run_resolver,
)


class ObjectDetectionEvaluationConfig(BaseModel):
    """Configuration for object-detection evaluation runs.

    Attributes:
        iou_threshold: IoU threshold used by object-detection evaluators.
            Stored in the run config for reproducibility.
        classwise: If True, match predictions and ground truths only within the
            same annotation class. If False, match globally across all annotation classes.
    """

    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    classwise: bool = True


class EvaluationResult(BaseModel):
    """Summary of the inputs used by an evaluation run.

    Returned by every task method on ``ImageDatasetEvaluate``. The field set is
    shared across tasks (object detection, classification, segmentation).

    Attributes:
        sample_count: Number of samples included in the evaluation.
        gt_annotation_count: Number of ground-truth annotations used.
        pred_annotation_count: Number of prediction annotations used.
    """

    sample_count: int
    gt_annotation_count: int
    pred_annotation_count: int

    @classmethod
    def from_evaluation_data(cls, data: EvaluationData) -> EvaluationResult:
        """Build a result from the prepared evaluation data."""
        return cls(
            sample_count=len(data.selected_sample_ids),
            gt_annotation_count=sum(len(v) for v in data.gt_per_sample.values()),
            pred_annotation_count=sum(len(v) for v in data.pred_per_sample.values()),
        )


class ClassificationEvaluationConfig(BaseModel):
    """Configuration for classification evaluation runs.

    Currently has no fields. Placeholder for future task-specific options.
    """


class ImageDatasetEvaluate:
    """Task-specific evaluation entry points for image datasets.

    This facade groups evaluation methods by task (e.g. object detection)
    and keeps evaluation-specific logic separate from ``ImageDataset``.
    """

    def __init__(
        self, session: Session, collection_id: UUID, samples: Iterable[ImageSample]
    ) -> None:
        """Initialize the evaluator facade.

        Args:
            session: Database session used by resolver calls.
            collection_id: ID of the collection being evaluated.
            samples: Samples selected for evaluation.
        """
        self.session = session
        self.collection_id = collection_id
        self.samples = samples

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
            gt_annotation_source: Name of the annotation source containing ground-truth annotations.
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
        object_detection_metric.create_and_persist_object_detection_metrics_per_sample(
            session=self.session,
            data=data,
            iou_threshold=config.iou_threshold,
            classwise=config.classwise,
        )
        return EvaluationResult.from_evaluation_data(data)

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
            gt_annotation_source: Name of the annotation source containing ground-truth annotations.
            pred_annotation_source: Name of the annotation source containing all annotations.
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
        return EvaluationResult.from_evaluation_data(data)

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
        gt_collection_id, pred_collection_id, evaluation_run = self._create_evaluation_run(
            name=name,
            gt_annotation_source=gt_annotation_source,
            pred_annotation_source=pred_annotation_source,
            task_type=task_type,
            config_json=config_json,
        )

        selected_sample_ids = {sample.sample_id for sample in self.samples}
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
                ground-truth annotations.
            pred_annotation_source: Name of the annotation source containing
                predictions.
            task_type: Evaluation task type; determines the expected annotation type
                for both collections and is stored on the run.
            config_json: Task-specific configuration to persist on the run.

        Returns:
            Tuple of (gt_collection_id, pred_collection_id, evaluation_run).
        """
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
