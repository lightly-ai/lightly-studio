"""Shared types for evaluation runners."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class MatchRecordLike(Protocol):
    """Protocol for persisted per-annotation match records."""

    sample_id: UUID
    pred_id: UUID | None
    gt_id: UUID | None
    iou: float | None
    match_type: str


@dataclass
class EvaluationRunResult:
    """Task-specific evaluation output."""

    metrics: dict[str, object]
    match_records: Sequence[MatchRecordLike]
