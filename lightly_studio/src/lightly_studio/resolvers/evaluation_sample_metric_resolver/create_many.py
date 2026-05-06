"""Bulk-insert evaluation sample metrics."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import EvaluationSampleMetricTable


def create_many(
    session: Session,
    records: Sequence[EvaluationSampleMetricTable],
) -> None:
    """Bulk-insert evaluation sample metric records.

    All records are inserted in a single database round-trip. No validation is
    performed on foreign keys; callers are responsible for ensuring that the
    referenced evaluation_run_id and sample_id exist.
    """
    if not records:
        return
    session.bulk_save_objects(list(records))
    session.commit()
