"""Persist an evaluation result."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_result import EvaluationResultTable, EvaluationTaskType


def create(  # noqa: PLR0913
    session: Session,
    dataset_id: UUID,
    name: str,
    gt_collection_id: UUID,
    prediction_collection_id: UUID,
    task_type: EvaluationTaskType,
    iou_threshold: float,
    confidence_threshold: float,
    metrics: dict[str, Any],
) -> EvaluationResultTable:
    """Create and persist an EvaluationResultTable entry (without committing)."""
    record = EvaluationResultTable(
        dataset_id=dataset_id,
        name=name,
        gt_collection_id=gt_collection_id,
        prediction_collection_id=prediction_collection_id,
        task_type=task_type,
        iou_threshold=iou_threshold,
        confidence_threshold=confidence_threshold,
        metrics=metrics,
    )
    session.add(record)
    session.flush()
    session.refresh(record)
    return record
