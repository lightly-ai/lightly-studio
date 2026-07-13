"""This module contains the API routes for managing collections."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import HTTP_STATUS_BAD_REQUEST, HTTP_STATUS_NOT_FOUND
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import (
    MetadataKeyNotFoundError,
    TagNotFoundError,
    UnsupportedMetadataTypeError,
)
from lightly_studio.metadata import compute_similarity, compute_typicality
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.metadata import (
    GPSCoordinateView,
    MetadataDistributionView,
    MetadataInfoView,
)
from lightly_studio.resolvers import embedding_model_resolver
from lightly_studio.resolvers.grid_filter import GridFilter
from lightly_studio.resolvers.metadata_resolver.sample.get_gps_coordinates import (
    get_gps_coordinates,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_distribution import (
    DEFAULT_BINS,
    get_metadata_distribution,
)
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    get_all_metadata_keys_and_schema,
)

metadata_router = APIRouter(prefix="/collections/{collection_id}", tags=["metadata"])


@metadata_router.get("/metadata/info", response_model=list[MetadataInfoView])
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


class MetadataDistributionRequest(BaseModel):
    """Request model for the metadata distribution endpoint."""

    filter: GridFilter | None = Field(
        default=None,
        description="Optional grid filter scoping the samples aggregated over.",
    )
    bins: int = Field(
        default=DEFAULT_BINS,
        gt=0,
        description="Number of equal-width bins for numeric keys.",
    )


@metadata_router.post(
    "/metadata/{key}/distribution",
    response_model=MetadataDistributionView,
)
def get_metadata_distribution_route(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    key: Annotated[str, Path(title="Metadata key")],
    request: MetadataDistributionRequest,
) -> MetadataDistributionView:
    """Get the distribution of a single metadata key.

    Categorical keys return value/count pairs (with an explicit ``(none)``
    entry); numeric keys return an equal-width histogram. An optional filter
    scopes the aggregation, e.g. to serve one series per tag.

    Args:
        session: The database session.
        collection: The validated collection.
        key: The metadata key to aggregate.
        request: Optional filter and numeric bin count.

    Returns:
        The distribution of the key over the (optionally filtered) samples.

    Raises:
        HTTPException: 404 if the key is absent; 400 if the key type is
            unsupported for a distribution.
    """
    scope_sample_ids: set[UUID] | None = None
    if request.filter is not None:
        scope_sample_ids = set(
            session.exec(
                request.filter.build_sample_ids_query(collection_id=collection.collection_id)
            ).all()
        )

    try:
        return get_metadata_distribution(
            session=session,
            collection_id=collection.collection_id,
            key=key,
            scope_sample_ids=scope_sample_ids,
            bins=request.bins,
        )
    except MetadataKeyNotFoundError as e:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=str(e)) from e
    except (UnsupportedMetadataTypeError, ValueError) as e:
        # ValueError covers schema/data drift (inconsistent schema types or a
        # non-numeric value under a numeric key) — a bad request, not a 500.
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(e)) from e


class GPSCoordinatesRequest(BaseModel):
    """Request model for the GPS coordinates endpoint."""

    filter: GridFilter | None = Field(
        default=None,
        description="Optional grid filter scoping the samples returned.",
    )


@metadata_router.post(
    "/metadata/{key}/gps",
    response_model=list[GPSCoordinateView],
)
def get_gps_coordinates_route(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    key: Annotated[str, Path(title="Metadata key")],
    request: GPSCoordinatesRequest,
) -> list[GPSCoordinateView]:
    """Return per-sample GPS coordinates (with sample tags) for the map.

    Only samples that have a value for the ``gps_coordinate`` ``key`` are
    returned; samples without GPS are omitted. An optional filter scopes the
    result to the active selection.

    Args:
        session: The database session.
        collection: The validated collection.
        key: The ``gps_coordinate`` metadata key to read.
        request: Optional filter scoping the samples returned.

    Returns:
        One entry per in-scope sample with GPS: ``{sample_id, lat, lon, tag_ids}``.

    Raises:
        HTTPException: 404 if the key is absent; 400 if the key is not a
            ``gps_coordinate`` key.
    """
    scope_sample_ids: set[UUID] | None = None
    if request.filter is not None:
        scope_sample_ids = set(
            session.exec(
                request.filter.build_sample_ids_query(collection_id=collection.collection_id)
            ).all()
        )

    try:
        return get_gps_coordinates(
            session=session,
            collection_id=collection.collection_id,
            key=key,
            scope_sample_ids=scope_sample_ids,
        )
    except MetadataKeyNotFoundError as e:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=str(e)) from e
    except (UnsupportedMetadataTypeError, ValueError) as e:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(e)) from e


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
