"""This module contains the API routes for managing collections."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_CONFLICT,
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.dataset import embedding_utils
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionOverviewView,
    CollectionTable,
    CollectionView,
    CollectionViewWithCount,
)
from lightly_studio.resolvers import collection_resolver

collection_router = APIRouter()


def get_and_validate_collection_id(
    session: SessionDep,
    collection_id: UUID,
) -> CollectionTable:
    """Get and validate the existence of a collection on a route."""
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if not collection:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Collection with ID {collection_id} not found.",
        )
    return collection


@collection_router.get("/collections", response_model=List[CollectionView])
def read_collections(
    session: SessionDep,
    paginated: Annotated[Paginated, Query()],
) -> list[CollectionTable]:
    """Retrieve a list of collections from the database."""
    return collection_resolver.get_all(
        session=session, offset=paginated.offset, limit=paginated.limit
    )


@collection_router.get("/collections/{collection_id}/dataset", response_model=CollectionView)
def read_dataset(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
) -> CollectionTable:
    """Retrieve the root collection for a given collection."""
    return collection_resolver.get_dataset(session=session, collection_id=collection_id)


@collection_router.get(
    "/collections/{collection_id}/hierarchy", response_model=List[CollectionView]
)
def read_collection_hierarchy(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Root collection Id")],
) -> list[CollectionTable]:
    """Retrieve the collection hierarchy from the database, starting with the root node."""
    return collection_resolver.get_hierarchy(session=session, dataset_id=collection_id)


@collection_router.get("/collections/overview", response_model=List[CollectionOverviewView])
def read_collections_overview(session: SessionDep) -> list[CollectionOverviewView]:
    """Retrieve collections with metadata for dashboard display."""
    return collection_resolver.get_collections_overview(session=session)


@collection_router.get("/collections/{collection_id}", response_model=CollectionViewWithCount)
def read_collection(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> CollectionViewWithCount:
    """Retrieve a single collection from the database."""
    return collection_resolver.get_collection_details(session=session, collection=collection)


@collection_router.put("/collections/{collection_id}")
def update_collection(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    collection_input: CollectionCreate,
) -> CollectionTable:
    """Update an existing collection in the database."""
    return collection_resolver.update(
        session=session,
        collection_id=collection.collection_id,
        collection_input=collection_input,
    )


@collection_router.delete("/collections/{collection_id}")
def delete_collection(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> dict[str, str]:
    """Delete a collection from the database."""
    collection_resolver.delete(session=session, collection_id=collection.collection_id)
    return {"status": "deleted"}


@collection_router.get("/collections/{collection_id}/has_embeddings")
def has_embeddings(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> bool:
    """Check if a collection has embeddings."""
    return embedding_utils.collection_has_embeddings(
        session=session, collection_id=collection.collection_id
    )


class DeepCopyRequest(BaseModel):
    """Request model for deep copy endpoint."""

    copy_name: str


@collection_router.post("/collections/{collection_id}/deep-copy", status_code=HTTP_STATUS_CREATED)
def deep_copy(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="Collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    request: DeepCopyRequest,
) -> dict[str, str]:
    """Create a deep copy of a collection with all related data."""
    if collection.parent_collection_id is not None:
        raise HTTPException(
            status_code=HTTP_STATUS_BAD_REQUEST,
            detail="Only root collections can be deep copied.",
        )

    existing = collection_resolver.get_by_name(session=session, name=request.copy_name)
    if existing:
        raise HTTPException(
            status_code=HTTP_STATUS_CONFLICT,
            detail=f"A collection with name '{request.copy_name}' already exists.",
        )

    new_collection = collection_resolver.deep_copy(
        session=session,
        root_collection_id=collection.collection_id,
        copy_name=request.copy_name,
    )

    return {"collection_id": str(new_collection.collection_id)}
