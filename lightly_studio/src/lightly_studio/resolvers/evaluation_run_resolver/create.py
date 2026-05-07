"""Persist an evaluation result."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionViewWithCount, SampleType
from lightly_studio.models.evaluation_run import EvaluationRunCreate, EvaluationRunTable
from lightly_studio.resolvers import collection_resolver


def create(session: Session, evaluation_run_input: EvaluationRunCreate) -> EvaluationRunTable:
    """Create and persist an EvaluationRunTable entry."""
    # Validate that gt and pred annotation collections exist, have the correct sample type,
    # and belong to the same dataset.
    gt_details = _validate_annotation_collection(
        session=session,
        collection_id=evaluation_run_input.gt_annotation_collection_id,
    )
    pred_details = _validate_annotation_collection(
        session=session,
        collection_id=evaluation_run_input.pred_annotation_collection_id,
    )

    if gt_details.dataset_id != pred_details.dataset_id:
        raise ValueError("gt and pred annotation collections must belong to the same dataset.")

    record = EvaluationRunTable.model_validate(evaluation_run_input)
    session.add(record)
    session.commit()
    session.refresh(record)
    return record


def _validate_annotation_collection(
    session: Session, collection_id: UUID
) -> CollectionViewWithCount:
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if collection is None:
        raise ValueError(f"Collection with id {collection_id} not found.")
    details = collection_resolver.get_collection_details(session=session, collection=collection)
    if details.sample_type != SampleType.ANNOTATION:
        raise ValueError(
            f"Collection with id {collection_id} has "
            f"sample type '{details.sample_type.value}', "
            f"expected '{SampleType.ANNOTATION.value}'."
        )
    return details
