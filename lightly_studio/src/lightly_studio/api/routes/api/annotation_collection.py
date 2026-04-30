"""API routes for managing annotation collections (named groups of GT or predictions)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.core.evaluation.register_gt_collection import (
    register_annotation_collection,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_collection import (
    AnnotationCollectionCreate,
    AnnotationCollectionView,
)
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_collection_resolver

annotation_collection_router = APIRouter(
    prefix="/datasets/{dataset_id}", tags=["annotation-collections"]
)


def _get_root_collection_or_404(
    session: SessionDep,
    root_collection_id: UUID,
) -> CollectionTable:
    """Resolve the route-level dataset identifier to the root collection row."""
    root_collection = session.get(CollectionTable, root_collection_id)
    if root_collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Dataset {root_collection_id} not found.",
        )
    return root_collection


@annotation_collection_router.get(
    "/annotation-collections",
    response_model=list[AnnotationCollectionView],
)
def list_annotation_collections(
    dataset_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> list[AnnotationCollectionView]:
    """List all annotation collections for a dataset."""
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)
    records = annotation_collection_resolver.get_all(
        session=session, dataset_id=root_collection.dataset_id
    )
    return [AnnotationCollectionView.model_validate(r) for r in records]


@annotation_collection_router.post(
    "/annotation-collections",
    response_model=AnnotationCollectionView,
    status_code=201,
)
def create_annotation_collection(
    dataset_id: Annotated[UUID, Path()],
    session: SessionDep,
    body: AnnotationCollectionCreate,
) -> AnnotationCollectionView:
    """Register an annotation collection by name.

    The underlying annotation child collection must already exist (i.e. annotations
    have been loaded via add_samples_from_coco or add_predictions_from_coco).
    """
    root_collection = _get_root_collection_or_404(session=session, root_collection_id=dataset_id)

    record = register_annotation_collection(
        session=session,
        dataset_id=root_collection.dataset_id,
        root_collection_id=root_collection.collection_id,
        collection_name=body.name,
        is_ground_truth=body.is_ground_truth,
        processed_sample_count=body.processed_sample_count,
        notes=body.notes,
    )
    return AnnotationCollectionView.model_validate(record)
