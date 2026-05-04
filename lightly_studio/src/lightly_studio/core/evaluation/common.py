"""Shared types and helpers for evaluation runners."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


class MatchRecordLike(Protocol):
    """Protocol for per-annotation match records produced by compute modules."""

    sample_id: UUID
    pred_id: UUID | None
    gt_id: UUID | None
    iou: float | None
    match_type: str
    label_id: UUID


@dataclass
class AnnotationResultRecord:
    """One annotation pairing to persist in EvaluationAnnotationResultTable."""

    sample_id: UUID
    pred_annotation_id: UUID | None
    gt_annotation_id: UUID | None
    metrics: dict[str, float]


@dataclass
class EvaluationRunResult:
    """Task-specific evaluation output."""

    metrics: dict[str, object]
    annotation_results: list[AnnotationResultRecord]
    sample_metrics: dict[tuple[UUID, UUID | None], dict[str, float]]


def build_results_from_matches(
    match_records: Sequence[MatchRecordLike],
    include_iou: bool = False,
) -> tuple[list[AnnotationResultRecord], dict[tuple[UUID, UUID | None], dict[str, float]]]:
    """Convert match records into annotation results and per-sample metric dicts.

    Args:
        match_records: Match records from a compute module.
        include_iou: If True, add ``{"iou": value}`` to TP annotation metrics.

    Returns:
        Tuple of (annotation_results, sample_metrics) where sample_metrics maps
        (sample_id, label_id) → {metric_name: value}.  label_id is None for the
        aggregate row (all classes combined), or the real label UUID for per-class rows.
    """
    annotation_results: list[AnnotationResultRecord] = []
    sample_metrics: dict[tuple[UUID, UUID | None], dict[str, float]] = {}

    for match in match_records:
        ann_metrics: dict[str, float] = {}
        if include_iou and match.match_type == "TP" and match.iou is not None:
            ann_metrics["iou"] = match.iou

        annotation_results.append(
            AnnotationResultRecord(
                sample_id=match.sample_id,
                pred_annotation_id=match.pred_id,
                gt_annotation_id=match.gt_id,
                metrics=ann_metrics,
            )
        )

        mt = match.match_type.lower()

        # Aggregate row (no class filter)
        agg_key: tuple[UUID, UUID | None] = (match.sample_id, None)
        agg = sample_metrics.setdefault(agg_key, {"tp": 0.0, "fp": 0.0, "fn": 0.0})
        agg[mt] = agg[mt] + 1.0

        # Per-class row
        cls_key: tuple[UUID, UUID | None] = (match.sample_id, match.label_id)
        cls = sample_metrics.setdefault(cls_key, {"tp": 0.0, "fp": 0.0, "fn": 0.0})
        cls[mt] = cls[mt] + 1.0

    return annotation_results, sample_metrics
