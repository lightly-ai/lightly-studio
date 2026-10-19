"""Validate evaluation parameters before rerunning with the saved sources."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlmodel import Session

from lightly_studio.evaluation.image_dataset_evaluate import (
    ClassificationEvaluationConfig,
    EvaluationResult,
    InstanceSegmentationEvaluationConfig,
    ObjectDetectionEvaluationConfig,
    SemanticSegmentationEvaluationConfig,
)
from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType
from lightly_studio.services import evaluation_service


class EvaluationRunUpdate(BaseModel):
    """New parameters for the saved task; other evaluation settings stay unchanged."""

    model_config = ConfigDict(extra="forbid")
    config: dict[str, Any]


def update_evaluation_run(
    session: Session, run: EvaluationRunTable, settings: EvaluationRunUpdate
) -> EvaluationResult:
    """Validate parameters and replace settings and results in one transaction."""
    config_types: dict[EvaluationTaskType, type[BaseModel]] = {
        EvaluationTaskType.OBJECT_DETECTION: ObjectDetectionEvaluationConfig,
        EvaluationTaskType.CLASSIFICATION: ClassificationEvaluationConfig,
        EvaluationTaskType.INSTANCE_SEGMENTATION: InstanceSegmentationEvaluationConfig,
        EvaluationTaskType.SEMANTIC_SEGMENTATION: SemanticSegmentationEvaluationConfig,
    }
    config_type = config_types[run.task_type]
    unknown = settings.config.keys() - config_type.model_fields.keys()
    if unknown:
        raise ValueError(f"Unknown evaluation parameters: {', '.join(sorted(unknown))}.")
    config = config_type.model_validate(settings.config)
    return evaluation_service.recompute_evaluation_run(
        session=session, run=run, config_json=config.model_dump()
    )
