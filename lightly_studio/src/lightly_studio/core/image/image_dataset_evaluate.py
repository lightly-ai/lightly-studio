"""Evaluation interface for image datasets."""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import Session

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


class ImageDatasetEvaluate:
    """Task-specific evaluation entry points for image datasets.

    This facade groups evaluation methods by task (e.g. object detection)
    and keeps evaluation-specific logic separate from ``ImageDataset``.
    """

    def __init__(self, session: Session) -> None:
        """Initialize the evaluator facade with a DB session."""
        self.session = session

    def object_detection(
        self,
        name: str,
        gt_collection_id: UUID,
        pred_collection_id: UUID,
        config: ObjectDetectionEvaluationConfig | None = None,
    ) -> Mapping[str, float]:
        """Create an object-detection evaluation run.

        For now, this method only persists an ``EvaluationRun`` entry.
        Metric computation and metric persistence are intentionally deferred.

        Args:
            name: Display name of the evaluation run.
            gt_collection_id: Annotation collection ID containing ground truth labels.
            pred_collection_id: Annotation collection ID containing predictions.
            config: Optional object-detection evaluation config. If omitted,
                defaults are used.

        Returns:
            Empty mapping for now. Future implementations can return aggregate
            metrics once metric computation is enabled.
        """
        config = config or ObjectDetectionEvaluationConfig()

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
