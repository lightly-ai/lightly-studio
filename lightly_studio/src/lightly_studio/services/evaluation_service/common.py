"""Shared helpers for task-specific evaluation runners."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.models.evaluation_match import EvaluationMatchTable, MatchType
from lightly_studio.models.evaluation_result_sample import EvaluationResultSampleTable
from lightly_studio.resolvers import annotation_collection_resolver


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


def resolve_annotation_collections(
    session: Session,
    dataset_id: UUID,
    gt_collection_name: str,
    prediction_collection_name: str,
) -> tuple[AnnotationCollectionTable, AnnotationCollectionTable]:
    """Resolve GT and prediction annotation collections by name."""
    gt = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=gt_collection_name
    )
    if gt is None:
        raise ValueError(f"Ground-truth collection '{gt_collection_name}' not found.")

    pred = annotation_collection_resolver.get_by_name(
        session=session, dataset_id=dataset_id, name=prediction_collection_name
    )
    if pred is None:
        raise ValueError(f"Prediction collection '{prediction_collection_name}' not found.")

    return (gt, pred)

def persist_matches(
    session: Session,
    evaluation_result_id: UUID,
    records: Sequence[MatchRecordLike],
) -> None:
    """Persist task-specific match records into the shared evaluation table."""
    rows = [
        EvaluationMatchTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=record.sample_id,
            pred_annotation_id=record.pred_id,
            gt_annotation_id=record.gt_id,
            iou=record.iou,
            match_type=MatchType(record.match_type),
        )
        for record in records
    ]
    session.add_all(rows)
    session.flush()


def persist_sample_ids(
    session: Session,
    evaluation_result_id: UUID,
    sample_ids: Sequence[UUID],
) -> None:
    """Persist the frozen sample snapshot for one evaluation run."""
    rows = [
        EvaluationResultSampleTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=sample_id,
        )
        for sample_id in sample_ids
    ]
    session.add_all(rows)
    session.flush()
