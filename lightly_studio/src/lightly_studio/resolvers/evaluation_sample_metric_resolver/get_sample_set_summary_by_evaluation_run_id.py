"""Summarize the set of samples that an evaluation run evaluated."""

from __future__ import annotations

import hashlib
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.evaluation_metrics import EvaluatedSampleSetSummary
from lightly_studio.resolvers.evaluation_sample_metric_resolver.get_sample_ids_by_evaluation_run_id import (  # noqa: E501
    get_sample_ids_by_evaluation_run_id,
)


def get_sample_set_summary_by_evaluation_run_id(
    session: Session,
    evaluation_run_id: UUID,
    tag_id: UUID | None = None,
) -> EvaluatedSampleSetSummary:
    """Return the count and a fingerprint of the samples that a run evaluated.

    Two runs that evaluated the same samples have the same fingerprint.

    Args:
        session: Database session.
        evaluation_run_id: The evaluation run.
        tag_id: If set, count only the evaluated images with this tag.

    Returns:
        The number of distinct samples with metrics, and a SHA-256 hash of their sorted IDs.
    """
    sample_ids = get_sample_ids_by_evaluation_run_id(
        session=session, evaluation_run_id=evaluation_run_id, tag_id=tag_id
    )
    joined_ids = ",".join(str(sample_id) for sample_id in sample_ids)
    return EvaluatedSampleSetSummary(
        sample_count=len(sample_ids),
        sample_set_hash=hashlib.sha256(joined_ids.encode()).hexdigest(),
    )
