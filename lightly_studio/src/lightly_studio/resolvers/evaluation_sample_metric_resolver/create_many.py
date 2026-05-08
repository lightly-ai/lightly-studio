"""Bulk-insert evaluation sample metrics."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from lightly_studio.models.evaluation_sample_metric import (
    EvaluationSampleMetricCreate,
    EvaluationSampleMetricTable,
)


def create_many(
    session: Session,
    records: Sequence[EvaluationSampleMetricCreate],
) -> None:
    """Bulk-insert evaluation sample metric records.

    All records are inserted in a single database round-trip. No validation is
    performed on foreign keys; callers are responsible for ensuring that the
    referenced evaluation_run_id and sample_id exist.
    """
    if not records:
        return
    table_records = [EvaluationSampleMetricTable.model_validate(obj=record) for record in records]
    session.bulk_save_objects(objects=table_records)
    session.commit()
