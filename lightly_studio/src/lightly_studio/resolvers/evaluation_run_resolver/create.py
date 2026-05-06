"""Persist an evaluation result."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationRunTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, evaluation_run_input: EvaluationRunCreate) -> EvaluationRunTable:
    """Create and persist an EvaluationRunTable entry."""
    # Validate that gt and pred annotation collections exist, have the correct sample type,
    # and belong to the same dataset.
    gt_collection = collection_resolver.get_by_id(
        session=session, collection_id=evaluation_run_input.gt_annotation_collection_id
    )
    if gt_collection is None:
        raise ValueError(
            f"Collection with id {evaluation_run_input.gt_annotation_collection_id} not found."
        )
    gt_details = collection_resolver.get_collection_details(
        session=session, collection=gt_collection
    )
    if gt_details.sample_type != SampleType.ANNOTATION:
        raise ValueError(
            f"Collection with id {evaluation_run_input.gt_annotation_collection_id} has "
            f"sample type '{gt_details.sample_type.value}', "
            f"expected '{SampleType.ANNOTATION.value}'."
        )

    pred_collection = collection_resolver.get_by_id(
        session=session, collection_id=evaluation_run_input.pred_annotation_collection_id
    )
    if pred_collection is None:
        raise ValueError(
            f"Collection with id {evaluation_run_input.pred_annotation_collection_id} not found."
        )
    pred_details = collection_resolver.get_collection_details(
        session=session, collection=pred_collection
    )
    if pred_details.sample_type != SampleType.ANNOTATION:
        raise ValueError(
            f"Collection with id {evaluation_run_input.pred_annotation_collection_id} has "
            f"sample type '{pred_details.sample_type.value}', "
            f"expected '{SampleType.ANNOTATION.value}'."
        )

    if gt_details.dataset_id != pred_details.dataset_id:
        raise ValueError(
            "gt and pred annotation collections must belong to the same dataset."
        )

    record = EvaluationRunTable.model_validate(evaluation_run_input)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record
