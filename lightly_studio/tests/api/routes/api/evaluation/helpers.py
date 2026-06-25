"""Shared helpers for the evaluation route tests."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from lightly_studio.models.evaluation_run import EvaluationRunTable, EvaluationTaskType


def make_evaluation_run(  # noqa: PLR0913
    *,
    run_id: UUID,
    name: str,
    config_json: dict[str, Any],
    created_at: datetime,
    gt_annotation_collection_id: UUID | None = None,
    pred_annotation_collection_id: UUID | None = None,
    task_type: EvaluationTaskType = EvaluationTaskType.OBJECT_DETECTION,
) -> EvaluationRunTable:
    return EvaluationRunTable(
        id=run_id,
        name=name,
        gt_annotation_collection_id=gt_annotation_collection_id or uuid4(),
        pred_annotation_collection_id=pred_annotation_collection_id or uuid4(),
        task_type=task_type,
        config_json=config_json,
        created_at=created_at,
    )
