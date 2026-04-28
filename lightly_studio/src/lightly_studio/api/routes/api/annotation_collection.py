"""API routes for managing annotation collections (named groups of GT or predictions)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_collection import (
    AnnotationCollectionCreate,
    AnnotationCollectionView,
)
from sqlmodel import col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_collection_resolver
from lightly_studio.services.evaluation_service.register_gt_collection import (
    register_annotation_collection,
)

annotation_collection_router = APIRouter(
    prefix="/datasets/{dataset_id}", tags=["annotation-collections"]
)


@annotation_collection_router.get(
    "/annotation-collections",
    response_model=list[AnnotationCollectionView],
)
def list_annotation_collections(
    dataset_id: Annotated[UUID, Path()],
    session: SessionDep,
) -> list[AnnotationCollectionView]:
    """List all annotation collections for a dataset."""
    records = annotation_collection_resolver.get_all(session=session, dataset_id=dataset_id)
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
    root_collection = session.exec(
        select(CollectionTable)
        .where(col(CollectionTable.dataset_id) == dataset_id)
        .where(col(CollectionTable.parent_collection_id).is_(None))
    ).first()
    if root_collection is None:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Dataset {dataset_id} not found.",
        )

    record = register_annotation_collection(
        session=session,
        dataset_id=dataset_id,
        root_collection_id=root_collection.collection_id,
        collection_name=body.name,
        is_ground_truth=body.is_ground_truth,
        processed_sample_count=body.processed_sample_count,
        notes=body.notes,
    )
    return AnnotationCollectionView.model_validate(record)
