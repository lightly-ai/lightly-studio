"""This module contains the API routes for managing collections."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.db_manager import SessionDep
from lightly_studio.errors import TagNotFoundError
from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.metadata import MetadataInfoView
from lightly_studio.resolvers import embedding_model_resolver
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    get_all_metadata_keys_and_schema,
)

metadata_router = APIRouter(prefix="/collections/{collection_id}", tags=["metadata"])


@metadata_router.get("/metadata/info", response_model=List[MetadataInfoView])
def get_metadata_info(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
) -> list[MetadataInfoView]:
    """Get all metadata keys and their schema for a collection.

    Args:
        session: The database session.
        collection_id: The ID of the collection.

    Returns:
        List of metadata info objects with name, type, and optionally min/max values
        for numerical metadata types.
    """
    return get_all_metadata_keys_and_schema(session=session, collection_id=collection_id)


class ComputeTypicalityRequest(BaseModel):
    """Request model for computing typicality metadata."""

    embedding_model_name: str | None = Field(
        default=None,
        description="Embedding model name (uses default if not specified)",
    )
    metadata_name: str = Field(
        default="typicality",
        description="Metadata field name (defaults to 'typicality')",
    )


@metadata_router.post(
    "/metadata/typicality",
    status_code=204,
    response_model=None,
)
def compute_typicality_metadata(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    request: ComputeTypicalityRequest,
) -> None:
    """Compute typicality metadata for a collection.

    Args:
        session: The database session.
        collection: The collection to compute typicality for.
        request: Request parameters including optional embedding model name
            and metadata field name.

    Returns:
        None (204 No Content on success).
    """
    embedding_model = embedding_model_resolver.get_by_name(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_name=request.embedding_model_name,
    )

    compute_typicality.compute_typicality_metadata(
        session=session,
        collection_id=collection.collection_id,
        embedding_model_id=embedding_model.embedding_model_id,
        metadata_name=request.metadata_name,
    )


class ComputeSimilarityRequest(BaseModel):
    """Request model for computing typicality metadata."""

    embedding_model_name: str | None = Field(
        default=None,
        description="Embedding model name (uses default if not specified)",
    )
    metadata_name: str | None = Field(
        default=None,
        description="Metadata field name (defaults to None)",
    )


@metadata_router.post(
    "/metadata/similarity/{query_tag_id}",
    response_model=str,
)
def compute_similarity_metadata(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    query_tag_id: Annotated[UUID, Path(title="Query Tag ID")],
    request: ComputeSimilarityRequest,
) -> str:
    """Compute similarity metadata for a collection.

    Args:
        session: The database session.
        collection: The collection to compute similarity for.
        query_tag_id: The ID of the tag to use for the query
        request: Request parameters including optional embedding model name
            and metadata field name.

    Returns:
        Metadata name used for the similarity.

    Raises:
        HTTPException: 404 if invalid embedding model or query tag is given.
    """
    try:
        embedding_model = embedding_model_resolver.get_by_name(
            session=session,
            collection_id=collection.collection_id,
            embedding_model_name=request.embedding_model_name,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Embedding model not found",
        ) from e

    try:
        return compute_similarity.compute_similarity_metadata(
            session=session,
            key_collection_id=collection.collection_id,
            query_tag_id=query_tag_id,
            embedding_model_id=embedding_model.embedding_model_id,
            metadata_name=request.metadata_name,
        )
    except TagNotFoundError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Query tag {query_tag_id} not found",
        ) from e
