"""Persist an evaluation result."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_result import EvaluationResultTable


def create(
    session: Session,
    dataset_id: UUID,
    gt_collection_id: UUID,
    prediction_collection_ids: list[UUID],
    iou_threshold: float,
    confidence_threshold: float,
    metrics: dict[str, Any],
) -> EvaluationResultTable:
    """Create and persist an EvaluationResultTable entry."""
    record = EvaluationResultTable(
        dataset_id=dataset_id,
        gt_collection_id=gt_collection_id,
        prediction_collection_ids=[
            str(collection_id) for collection_id in prediction_collection_ids
        ],
        iou_threshold=iou_threshold,
        confidence_threshold=confidence_threshold,
        metrics=metrics,
    )
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
