"""This module contains the API routes for managing samples."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import AnnotationView
from lightly_studio.models.caption import CaptionView
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import (
    ImageView,
    ImageViewsWithCount,
)
from lightly_studio.models.metadata import SampleMetadataView
from lightly_studio.models.sample import SampleView
from lightly_studio.resolvers import (
    image_resolver,
)
from lightly_studio.resolvers.image_filter import (
    ImageFilter,
)

image_router = APIRouter(prefix="/collections/{collection_id}", tags=["image"])


class ReadImagesRequest(BaseModel):
    """Request body for reading samples with text embedding."""

    filters: ImageFilter | None = Field(None, description="Filter parameters for samples")
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(
        None, description="Pagination parameters for offset and limit"
    )


@image_router.post("/images/list")
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
    result = image_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=body.pagination,
        filters=body.filters,
        text_embedding=body.text_embedding,
        sample_ids=body.sample_ids,
    )
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    scores: list[float | None] = (
        list(result.similarity_scores) if result.similarity_scores else [None] * len(result.samples)
    )
    return ImageViewsWithCount(
        samples=[
            ImageView(
                file_name=image.file_name,
                file_path_abs=image.file_path_abs,
                sample_id=image.sample_id,
                annotations=[
                    AnnotationView.model_validate(annotation)
                    for annotation in image.sample.annotations
                ],
                captions=[CaptionView.model_validate(caption) for caption in image.sample.captions],
                tags=[
                    ImageView.ImageViewTag(
                        tag_id=tag.tag_id,
                        name=tag.name,
                        kind=tag.kind,
                        created_at=tag.created_at,
                        updated_at=tag.updated_at,
                    )
                    for tag in image.sample.tags
                ],
                metadata_dict=SampleMetadataView.model_validate(image.sample.metadata_dict)
                if image.sample.metadata_dict
                else None,
                width=image.width,
                height=image.height,
                sample=SampleView.model_validate(image.sample),
                similarity_score=score,
            )
            for image, score in zip(result.samples, scores)
        ],
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@image_router.get("/images/dimensions")
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
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    return ImageView(
        file_name=image.file_name,
        file_path_abs=image.file_path_abs,
        sample_id=image.sample_id,
        annotations=[
            AnnotationView.model_validate(annotation) for annotation in image.sample.annotations
        ],
        captions=[CaptionView.model_validate(caption) for caption in image.sample.captions],
        tags=[
            ImageView.ImageViewTag(
                tag_id=tag.tag_id,
                name=tag.name,
                kind=tag.kind,
                created_at=tag.created_at,
                updated_at=tag.updated_at,
            )
            for tag in image.sample.tags
        ],
        metadata_dict=SampleMetadataView.model_validate(image.sample.metadata_dict)
        if image.sample.metadata_dict
        else None,
        width=image.width,
        height=image.height,
        sample=SampleView.model_validate(image.sample),
    )


class SampleAdjacentsParams(BaseModel):
    """Parameters for getting adjacent samples."""

    filters: ImageFilter | None = None
    text_embedding: list[float] | None = None
