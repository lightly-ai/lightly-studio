"""Persist an evaluation result."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationRunTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, evaluation_run_input: EvaluationRunCreate) -> EvaluationRunTable:
    """Create and persist an EvaluationRunTable entry (without committing)."""
    # Validate that the provided annotation collection IDs exist and have the correct sample type.
    collection_resolver.check_collection_type(
        session=session,
        collection_id=evaluation_run_input.gt_annotation_collection_id,
        expected_type=SampleType.ANNOTATION,
    )
    collection_resolver.check_collection_type(
        session=session,
        collection_id=evaluation_run_input.pred_annotation_collection_id,
        expected_type=SampleType.ANNOTATION,
    )

    record = EvaluationRunTable.model_validate(evaluation_run_input)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
