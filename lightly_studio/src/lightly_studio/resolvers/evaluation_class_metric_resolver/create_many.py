"""Bulk-insert evaluation class metrics."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from lightly_studio.models.evaluation_class_metric import (
    EvaluationClassMetricCreate,
    EvaluationClassMetricTable,
)


def create_many(
    session: Session,
    records: Sequence[EvaluationClassMetricCreate],
) -> None:
    """Bulk-insert evaluation class metric records.

    All records are inserted in a single database round-trip. No validation is
    performed on foreign keys; callers are responsible for ensuring that the
    referenced evaluation_run_id exists.
    """
    if not records:
        return
    table_records = [EvaluationClassMetricTable.model_validate(obj=record) for record in records]
    session.bulk_save_objects(objects=table_records)
    session.commit()
