"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.evaluation.object_detection_metric import BoundingBox, match_image
from lightly_studio.evaluation.validators import resolve_and_validate_collection
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricCreate
from lightly_studio.resolvers import (
    annotation_collection_coverage_resolver,
    annotation_resolver,
    evaluation_run_resolver,
    evaluation_sample_metric_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter

SAMPLE_BATCH_SIZE = 32  # Number of samples to process in a single batch


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
        gt_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=gt_collection_name,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        )
        pred_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=pred_collection_name,
            task_type=EvaluationTaskType.OBJECT_DETECTION,
        )
        evaluation_run = evaluation_run_resolver.create(
            session=self.session,
            evaluation_run_input=EvaluationRunCreate(
                name=name,
                gt_annotation_collection_id=gt_collection_id,
                pred_annotation_collection_id=pred_collection_id,
                task_type=EvaluationTaskType.OBJECT_DETECTION,
                config_json=config.model_dump(),
            ),
        )

        gt_annotations = self._get_object_detection_annotations(collection_id=gt_collection_id)
        pred_annotations = self._get_object_detection_annotations(collection_id=pred_collection_id)

        gt_per_sample = self._group_by_parent_sample_id(annotations=gt_annotations)
        pred_per_sample = self._group_by_parent_sample_id(annotations=pred_annotations)
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

        self._create_and_persist_object_detection_metrics_per_sample(
            evaluation_run_id=evaluation_run.id,
            selected_sample_ids=selected_sample_ids,
            pred_per_sample=pred_per_sample,
            gt_per_sample=gt_per_sample,
            config=config,
        )

    def _get_object_detection_annotations(self, collection_id: UUID) -> list[AnnotationBaseTable]:
        """Return all object-detection annotations in the collection."""
        result = annotation_resolver.get_all(
            session=self.session,
            filters=AnnotationsFilter(
                collection_ids=[collection_id],
                annotation_types=[AnnotationType.OBJECT_DETECTION],
            ),
        )
        return list(result.annotations)

    @staticmethod
    def _group_by_parent_sample_id(
        annotations: list[AnnotationBaseTable],
    ) -> dict[UUID, list[AnnotationBaseTable]]:
        """Group annotation rows by their parent image sample id."""
        grouped: dict[UUID, list[AnnotationBaseTable]] = {}
        for annotation in annotations:
            grouped.setdefault(annotation.parent_sample_id, []).append(annotation)
        return grouped

    @staticmethod
    def _to_bounding_boxes(annotations: list[AnnotationBaseTable]) -> list[BoundingBox]:
        """Convert object-detection annotations into matcher-ready bounding boxes."""
        boxes: list[BoundingBox] = []
        for annotation in annotations:
            details = annotation.object_detection_details
            if details is None:
                continue
            boxes.append(
                BoundingBox(
                    annotation_id=annotation.sample_id,
                    x=details.x,
                    y=details.y,
                    width=details.width,
                    height=details.height,
                    label_id=annotation.annotation_label_id,
                    confidence=annotation.confidence,
                )
            )
        return boxes

    def _create_and_persist_object_detection_metrics_per_sample(
        self,
        evaluation_run_id: UUID,
        selected_sample_ids: set[UUID],
        pred_per_sample: dict[UUID, list[AnnotationBaseTable]],
        gt_per_sample: dict[UUID, list[AnnotationBaseTable]],
        config: ObjectDetectionEvaluationConfig,
    ) -> None:
        """Create and persist per-sample object-detection metrics."""
        metrics_to_persist: list[EvaluationSampleMetricCreate] = []
        for sample_id in selected_sample_ids:
            matching_result = match_image(
                predictions=self._to_bounding_boxes(annotations=pred_per_sample.get(sample_id, [])),
                ground_truths=self._to_bounding_boxes(annotations=gt_per_sample.get(sample_id, [])),
                iou_threshold=config.iou_threshold,
                classwise=config.classwise,
            )
            metrics_to_persist.extend(
                [
                    EvaluationSampleMetricCreate(
                        evaluation_run_id=evaluation_run_id,
                        sample_id=sample_id,
                        metric_name="tp",
                        value=float(matching_result.tp),
                    ),
                    EvaluationSampleMetricCreate(
                        evaluation_run_id=evaluation_run_id,
                        sample_id=sample_id,
                        metric_name="fp",
                        value=float(matching_result.fp),
                    ),
                    EvaluationSampleMetricCreate(
                        evaluation_run_id=evaluation_run_id,
                        sample_id=sample_id,
                        metric_name="fn",
                        value=float(matching_result.fn),
                    ),
                ]
            )
            if len(metrics_to_persist) >= SAMPLE_BATCH_SIZE:
                evaluation_sample_metric_resolver.create_many(
                    session=self.session,
                    records=metrics_to_persist,
                )
                metrics_to_persist.clear()
        if metrics_to_persist:
            evaluation_sample_metric_resolver.create_many(
                session=self.session,
                records=metrics_to_persist,
            )
