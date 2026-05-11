"""Persist an evaluation result."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationRunTable


def create(session: Session, evaluation_run_input: EvaluationRunCreate) -> EvaluationRunTable:
    """Create and persist an EvaluationRunTable entry.

    Collection existence and annotation type validations should be performed before calling this
    function.
    """
    record = EvaluationRunTable.model_validate(evaluation_run_input)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
