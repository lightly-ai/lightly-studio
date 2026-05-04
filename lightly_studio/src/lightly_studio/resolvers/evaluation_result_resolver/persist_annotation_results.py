"""Persist per-annotation pairing records for an evaluation run."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.evaluation.common import AnnotationResultRecord
from lightly_studio.models.evaluation_annotation_result import EvaluationAnnotationResultTable


def persist_annotation_results(
    session: Session,
    evaluation_result_id: UUID,
    results: Sequence[AnnotationResultRecord],
) -> None:
    """Bulk-insert annotation result rows without committing."""
    rows = [
        EvaluationAnnotationResultTable(
            evaluation_result_id=evaluation_result_id,
            sample_id=record.sample_id,
            pred_annotation_id=record.pred_annotation_id,
            gt_annotation_id=record.gt_annotation_id,
            metrics=record.metrics,
        )
        for record in results
    ]
    session.add_all(rows)
    session.flush()
