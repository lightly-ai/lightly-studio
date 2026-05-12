"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.evaluation.validators import resolve_and_validate_collection
from lightly_studio.models.evaluation_run import (
    EvaluationRunCreate,
    EvaluationTaskType,
)
from lightly_studio.resolvers import evaluation_run_resolver


class ObjectDetectionEvaluationConfig(BaseModel):
    """Configuration for object-detection evaluation runs.

    Attributes:
        iou_threshold: IoU threshold used by object-detection evaluators.
            Stored in the run config for reproducibility.
    """

    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)


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
    ) -> Mapping[str, float]:
        """Create an object-detection evaluation run.

        For now, this method only persists an ``EvaluationRun`` entry.
        Metric computation and metric persistence are intentionally deferred.

        Args:
            name: Display name of the evaluation run.
            gt_collection_name: Name of the annotation collection containing ground truth labels.
            pred_collection_name: Name of the annotation collection containing predictions.
            config: Optional object-detection evaluation config. If omitted,
                defaults are used.

        Returns:
            Empty mapping for now. Future implementations can return aggregate
            metrics once metric computation is enabled.
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
        evaluation_run_resolver.create(
            session=self.session,
            evaluation_run_input=EvaluationRunCreate(
                name=name,
                gt_annotation_collection_id=gt_collection_id,
                pred_annotation_collection_id=pred_collection_id,
                task_type=EvaluationTaskType.OBJECT_DETECTION,
                config_json=config.model_dump(),
            ),
        )
        return {}

    def classification(
        self,
        name: str,
        gt_collection_name: str,
        pred_collection_name: str,
        config: ClassificationEvaluationConfig | None = None,
    ) -> Mapping[str, float]:
        """Create a classification evaluation run.

        For now, this method only persists an ``EvaluationRun`` entry.
        Metric computation and metric persistence are intentionally deferred.

        Args:
            name: Display name of the evaluation run.
            gt_collection_name: Name of the annotation collection containing ground truth labels.
            pred_collection_name: Name of the annotation collection containing predictions.
            config: Optional classification evaluation config. If omitted,
                defaults are used.

        Returns:
            Empty mapping for now. Future implementations can return aggregate
            metrics once metric computation is enabled.
        """
        config = config or ClassificationEvaluationConfig()
        gt_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=gt_collection_name,
            task_type=EvaluationTaskType.CLASSIFICATION,
        )
        pred_collection_id = resolve_and_validate_collection(
            session=self.session,
            collection_id=self.collection_id,
            collection_name=pred_collection_name,
            task_type=EvaluationTaskType.CLASSIFICATION,
        )
        evaluation_run_resolver.create(
            session=self.session,
            evaluation_run_input=EvaluationRunCreate(
                name=name,
                gt_annotation_collection_id=gt_collection_id,
                pred_annotation_collection_id=pred_collection_id,
                task_type=EvaluationTaskType.CLASSIFICATION,
                config_json=config.model_dump(),
            ),
        )
        return {}
