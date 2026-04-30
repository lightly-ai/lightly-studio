"""Resolve annotation collections by name for evaluation."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation_collection import AnnotationCollectionTable
from lightly_studio.resolvers.annotation_collection_resolver.get_by_name import get_by_name


def resolve_collections(
    session: Session,
    dataset_id: UUID,
    gt_collection_name: str,
    prediction_collection_name: str,
) -> tuple[AnnotationCollectionTable, AnnotationCollectionTable]:
    """Resolve GT and prediction annotation collections by name, raising if either is missing."""
    gt = get_by_name(session=session, dataset_id=dataset_id, name=gt_collection_name)
    if gt is None:
        raise ValueError(f"Ground-truth collection '{gt_collection_name}' not found.")

    pred = get_by_name(
        session=session, dataset_id=dataset_id, name=prediction_collection_name
    )
    if pred is None:
        raise ValueError(f"Prediction collection '{prediction_collection_name}' not found.")

    return (gt, pred)
