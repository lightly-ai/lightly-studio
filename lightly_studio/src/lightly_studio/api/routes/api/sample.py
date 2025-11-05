"""This module contains the API routes for managing samples."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.dataset import get_and_validate_dataset_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.image import (
    ImageCreate,
    ImageTable,
    ImageView,
    ImageViewsWithCount,
)
from lightly_studio.models.sample import SamplesWithCount
from lightly_studio.resolvers import (
    image_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.samples_filter import (
    SampleFilter,
)

samples_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["samples"])


class ReadSamplesRequest(BaseModel):
    """Request body for reading samples with text embedding."""

    filters: SampleFilter | None = Field(None, description="Filter parameters for samples")
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(
        None, description="Pagination parameters for offset and limit"
    )


@samples_router.post("/samples/list")
def read_samples(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    body: ReadSamplesRequest,
) -> ImageViewsWithCount:
    """Retrieve a list of samples from the database with optional filtering.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to filter samples by.
        body: Optional request body containing text embedding.

    Returns:
        A list of filtered samples.
    """
    result = image_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
        pagination=body.pagination,
        filters=body.filters,
        text_embedding=body.text_embedding,
        sample_ids=body.sample_ids,
    )
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    return ImageViewsWithCount(
        samples=[
            ImageView(
                file_name=image.file_name,
                file_path_abs=image.file_path_abs,
                sample_id=image.sample_id,
                dataset_id=image.dataset_id,
                annotations=image.annotations,
                captions=image.sample.captions,
                tags=image.sample.tags,
                metadata_dict=image.sample.metadata_dict,
                width=image.width,
                height=image.height,
            )
            for image in result.samples
        ],
        total_count=result.total_count,
        next_cursor=result.next_cursor,
    )


@samples_router.get("/samples/dimensions")
def get_sample_dimensions(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
) -> dict[str, int]:
    """Get min and max dimensions of samples in a dataset."""
    return image_resolver.get_dimension_bounds(
        session=session,
        dataset_id=dataset.dataset_id,
        annotation_label_ids=annotation_label_ids,
    )


@samples_router.get("/samples/{sample_id}")
def read_sample(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> ImageView:
    """Retrieve a single sample from the database."""
    image = image_resolver.get_by_id(session=session, dataset_id=dataset_id, sample_id=sample_id)
    if not image:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")
    # TODO(Michal, 10/2025): Add SampleView to ImageView and then use a response model
    # instead of manual conversion.
    return ImageView(
        file_name=image.file_name,
        file_path_abs=image.file_path_abs,
        sample_id=image.sample_id,
        dataset_id=image.dataset_id,
        annotations=image.annotations,
        captions=image.sample.captions,
        tags=image.sample.tags,
        metadata_dict=image.sample.metadata_dict,
        width=image.width,
        height=image.height,
    )


@samples_router.put("/samples/{sample_id}")
def update_sample(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample Id")],
    sample_input: ImageCreate,
) -> ImageTable:
    """Update an existing sample in the database."""
    sample = image_resolver.update(session=session, sample_id=sample_id, sample_data=sample_input)
    if not sample:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")
    return sample


@samples_router.delete("/samples/{sample_id}")
def delete_sample(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> dict[str, str]:
    """Delete a sample from the database."""
    if not image_resolver.delete(session=session, dataset_id=dataset_id, sample_id=sample_id):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")
    return {"status": "deleted"}


@samples_router.post(
    "/samples/{sample_id}/tag/{tag_id}",
    status_code=HTTP_STATUS_CREATED,
)
def add_tag_to_sample(
    session: SessionDep,
    sample_id: UUID,
    # TODO(Michal, 10/2025): Remove unused dataset_id.
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],  # noqa: ARG001
    tag_id: UUID,
) -> bool:
    """Add sample to a tag."""
    sample = sample_resolver.get_by_id(session=session, sample_id=sample_id)
    if not sample:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Sample {sample_id} not found",
        )

    if not tag_resolver.add_tag_to_sample(session=session, tag_id=tag_id, sample=sample):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=f"Tag {tag_id} not found")

    return True


@samples_router.delete("/samples/{sample_id}/tag/{tag_id}")
def remove_tag_from_sample(
    session: SessionDep,
    tag_id: UUID,
    # TODO(Michal, 10/2025): Remove unused dataset_id.
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],  # noqa: ARG001
    sample_id: UUID,
) -> bool:
    """Remove sample from a tag."""
    sample = sample_resolver.get_by_id(session=session, sample_id=sample_id)
    if not sample:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Sample {sample_id} not found",
        )

    if not tag_resolver.remove_tag_from_sample(session=session, tag_id=tag_id, sample=sample):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=f"Tag {tag_id} not found")

    return True


@samples_router.get("/samples/captions/list", response_model=SamplesWithCount)
def read_samples_with_captions(
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> SamplesWithCount:
    """Retrieve samples with captions for a dataset."""
    return sample_resolver.get_all_samples_with_captions(
        session=session,
        dataset_id=dataset_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )


class SampleAdjacentsParams(BaseModel):
    """Parameters for getting adjacent samples."""

    filters: SampleFilter | None = None
    text_embedding: list[float] | None = None
