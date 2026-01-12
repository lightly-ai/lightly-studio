"""This module contains the API routes for managing collections."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
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
            detail=f""" Collection with {collection_id} not found.""",
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


@collection_router.post("/collections/{collection_id}/deep-copy-test")
def deep_copy_test(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id to copy")],
) -> dict[str, str]:
    """Test deep copy endpoint."""
    new_collection = collection_resolver.deep_copy(
        session=session,
        root_collection_id=collection_id,
        new_name="test_copy_dataset",
    )

    return {"new_collection_id": str(new_collection.collection_id)}
