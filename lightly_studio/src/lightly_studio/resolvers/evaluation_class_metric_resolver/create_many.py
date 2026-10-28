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
    """Bulk-insert evaluation class metric records."""
    if not records:
        return
    table_records = [EvaluationClassMetricTable.model_validate(obj=record) for record in records]
    session.bulk_save_objects(objects=table_records)
    session.commit()
