"""Bulk-insert evaluation annotation metrics."""

from __future__ import annotations

from collections.abc import Sequence

from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_metric import (
    EvaluationAnnotationMetricCreate,
    EvaluationAnnotationMetricTable,
)


def create_many(
    session: Session,
    records: Sequence[EvaluationAnnotationMetricCreate],
) -> None:
    """Bulk-insert evaluation annotation metric records."""
    if not records:
        return
    table_records = [
        EvaluationAnnotationMetricTable.model_validate(obj=record) for record in records
    ]
    session.bulk_save_objects(objects=table_records)
    session.commit()
