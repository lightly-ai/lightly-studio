"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.evaluation import object_detection_metric
from lightly_studio.evaluation.validators import resolve_and_validate_collection
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
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
            same class label. If False, match globally across all labels.
    """

    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    classwise: bool = True


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
        gt_collection_name: str,
        pred_collection_name: str,
        config: ObjectDetectionEvaluationConfig | None = None,
    ) -> None:
        """Create an object-detection evaluation run and persist per-image metrics.

        Args:
            name: Display name of the evaluation run.
            gt_collection_name: Name of the annotation collection containing ground truth labels.
            pred_collection_name: Name of the annotation collection containing predictions.
            config: Optional object-detection evaluation config. If omitted,
                defaults are used.
        """
        config = config or ObjectDetectionEvaluationConfig()
        gt_collection_id, pred_collection_id, evaluation_run = self._create_evaluation_run(
            name=name,
            gt_collection_name=gt_collection_name,
            pred_collection_name=pred_collection_name,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
            config_json=config.model_dump(),
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
        gt_annotations = annotation_resolver.get_all_by_parent_sample_ids(
            session=self.session,
            parent_sample_ids=list(selected_sample_ids),
            annotation_type=AnnotationType.OBJECT_DETECTION,
            annotation_collection_id=gt_collection_id,
        )
        pred_annotations = annotation_resolver.get_all_by_parent_sample_ids(
            session=self.session,
            parent_sample_ids=list(selected_sample_ids),
            annotation_type=AnnotationType.OBJECT_DETECTION,
            annotation_collection_id=pred_collection_id,
        )

        gt_per_sample = self._group_by_parent_sample_id(annotations=gt_annotations)
        pred_per_sample = self._group_by_parent_sample_id(annotations=pred_annotations)

        object_detection_metric.create_and_persist_object_detection_metrics_per_sample(
            session=self.session,
            evaluation_run_id=evaluation_run.id,
            selected_sample_ids=selected_sample_ids,
            pred_per_sample=pred_per_sample,
            gt_per_sample=gt_per_sample,
            iou_threshold=config.iou_threshold,
            classwise=config.classwise,
        )

    def classification(
        self,
        name: str,
        gt_collection_name: str,
        pred_collection_name: str,
        config: ClassificationEvaluationConfig | None = None,
    ) -> None:
        """Create a classification evaluation run.

        For now, this method only persists an ``EvaluationRun`` entry.
        Metric computation and metric persistence are intentionally deferred.

        Args:
            name: Display name of the evaluation run.
            gt_collection_name: Name of the annotation collection containing ground truth labels.
            pred_collection_name: Name of the annotation collection containing predictions.
            config: Optional classification evaluation config. If omitted,
                defaults are used.
        """
        config = config or ClassificationEvaluationConfig()
        self._create_evaluation_run(
            name=name,
            gt_collection_name=gt_collection_name,
            pred_collection_name=pred_collection_name,
            task_type=EvaluationTaskType.CLASSIFICATION,
            config_json=config.model_dump(),
        )

    def _create_evaluation_run(
        self,
        name: str,
        gt_collection_name: str,
        pred_collection_name: str,
        task_type: EvaluationTaskType,
        config_json: dict[str, Any],
    ) -> tuple[UUID, UUID, EvaluationRunTable]:
        """Validate gt + pred collections and persist the evaluation run.

        Args:
            name: Display name of the evaluation run.
            gt_collection_name: Name of the annotation collection containing ground
                truth labels.
            pred_collection_name: Name of the annotation collection containing
                predictions.
            task_type: Evaluation task type; determines the expected annotation type
                for both collections and is stored on the run.
            config_json: Task-specific configuration to persist on the run.

        Returns:
            Tuple of (gt_collection_id, pred_collection_id, evaluation_run).
        """
        gt_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=gt_collection_name,
            task_type=task_type,
        )
        pred_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=pred_collection_name,
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
