"""This module contains the API routes for managing samples."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_BAD_REQUEST,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.core.dataset_query.wire import WireExpression
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import (
    ImageView,
    ImageViewsWithCount,
)
from lightly_studio.resolvers import (
    image_resolver,
)
from lightly_studio.resolvers.image_filter import (
    ImageFilter,
)

image_router = APIRouter(tags=["image"])


class ReadImagesRequest(BaseModel):
    """Request body for reading samples with text embedding."""

    filters: ImageFilter | None = Field(None, description="Filter parameters for samples")
    query_filter: WireExpression | None = Field(
        None,
        description=(
            "Query filter tree built from the Python DatasetQuery API or the frontend "
            "query builder. Supported nodes: field, tags_contains, and, or, not."
        ),
    )
    python_query: str | None = Field(
        None,
        description="Python DatasetQuery expression evaluated server-side.",
    )
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(
        None, description="Pagination parameters for offset and limit"
    )


@image_router.post("/collections/{collection_id}/images/list")
def read_images(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="collection Id")],
    body: ReadImagesRequest,
) -> ImageViewsWithCount:
    """Retrieve a list of samples from the database with optional filtering.

    Args:
        session: The database session.
        collection_id: The ID of the collection to filter samples by.
        body: Optional request body containing text embedding.

    Returns:
        A list of filtered samples.
    """
    try:
        result = image_resolver.get_all_by_collection_id(
            session=session,
            collection_id=collection_id,
            pagination=body.pagination,
            filters=body.filters,
            query_filter=body.query_filter,
            python_query=body.python_query,
            text_embedding=body.text_embedding,
            sample_ids=body.sample_ids,
        )
    except ValueError as exc:
        raise HTTPException(status_code=HTTP_STATUS_BAD_REQUEST, detail=str(exc)) from exc
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    scores: list[float | None] = (
        list(result.similarity_scores) if result.similarity_scores else [None] * len(result.samples)
    )
    return ImageViewsWithCount(
        samples=[
            ImageView.from_image_table(image=image, similarity_score=score)
            for image, score in zip(result.samples, scores)
        ],
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@image_router.get("/collections/{collection_id}/images/dimensions")
def get_image_dimensions(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a collection."""
    return image_resolver.get_dimension_bounds(
        session=session,
        collection_id=collection.collection_id,
        annotation_label_ids=annotation_label_ids,
    )


@image_router.get("/images/{sample_id}")
def read_image(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> ImageView:
    """Retrieve a single sample from the database."""
    image = image_resolver.get_by_id(session=session, sample_id=sample_id)
    if not image:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")

    return ImageView.from_image_table(image=image)


class SampleAdjacentsParams(BaseModel):
    """Parameters for getting adjacent samples."""

    filters: ImageFilter | None = None
    text_embedding: list[float] | None = None


class ReadCountImageAnnotationsRequest(BaseModel):
    """Request body for reading image annotation counts."""

    filter: ImageFilter | None = None


@image_router.post("/collections/{collection_id}/images/annotations/count")
def count_image_annotations_by_collection(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ReadCountImageAnnotationsRequest | None = None,
) -> list[dict[str, str | int]]:
    """Get image annotation counts for a specific collection."""
    image_filter = body.filter if body and body.filter else None
    counts = image_resolver.count_image_annotations_by_collection(
        session=session,
        collection_id=collection.collection_id,
        image_filter=image_filter,
    )

    return [
        {
            "label_name": label_name,
            "current_count": current_count,
            "total_count": total_count,
        }
        for label_name, current_count, total_count in counts
    ]
