"""Summarize the set of samples that an evaluation run evaluated."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.evaluation_metrics import EvaluatedSampleSetSummary
from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable


def get_sample_set_summary_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
) -> EvaluatedSampleSetSummary:
    """Return the count and a fingerprint of the samples that a run evaluated.

    Two runs that evaluated the same samples have the same fingerprint.

    Args:
        session: Database session.
        evaluation_run_id: The evaluation run.

    Returns:
        The number of distinct samples with metrics, and a SHA-256 hash of their sorted IDs.
    """
    stmt = (
        select(EvaluationSampleMetricTable.sample_id)
        .where(col(EvaluationSampleMetricTable.evaluation_run_id) == evaluation_run_id)
        .distinct()
    )
    sorted_sample_ids = sorted(str(sample_id) for sample_id in session.exec(stmt).all())
    return EvaluatedSampleSetSummary(
        sample_count=len(sorted_sample_ids),
        sample_set_hash=hashlib.sha256(",".join(sorted_sample_ids).encode()).hexdigest(),
    )
