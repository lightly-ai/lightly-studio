"""Bulk-insert annotation match rows."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_annotation_match import (
    EvaluationAnnotationMatchCreate,
    EvaluationAnnotationMatchTable,
)


def create_many(
    session: Session,
    records: list[EvaluationAnnotationMatchCreate],
) -> None:
    """Bulk-insert annotation match records."""
    if not records:
        return
    rows = [EvaluationAnnotationMatchTable(**r.model_dump()) for r in records]
    session.add_all(rows)
    session.commit()
