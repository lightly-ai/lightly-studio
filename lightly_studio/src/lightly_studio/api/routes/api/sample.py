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
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.sample import (
    SampleCreate,
    SampleTable,
    SampleView,
    SampleViewsWithCount,
)
from lightly_studio.resolvers import (
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver import GetAllSamplesByDatasetIdResult
from lightly_studio.resolvers.samples_filter import (
    SampleFilter,
)

samples_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["samples"])


@samples_router.post("/samples", response_model=SampleView)
def create_sample(
    session: SessionDep,
    input_sample: SampleCreate,
) -> SampleTable:
    """Create a new sample in the database."""
    return sample_resolver.create(session=session, sample=input_sample)


class ReadSamplesRequest(BaseModel):
    """Request body for reading samples with text embedding."""

    filters: SampleFilter | None = Field(None, description="Filter parameters for samples")
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")
    sample_ids: list[UUID] | None = Field(None, description="The list of requested sample IDs")
    pagination: Paginated | None = Field(
        None, description="Pagination parameters for offset and limit"
    )


@samples_router.post("/samples/list", response_model=SampleViewsWithCount)
def read_samples(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
    body: ReadSamplesRequest,
) -> GetAllSamplesByDatasetIdResult:
    """Retrieve a list of samples from the database with optional filtering.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset to filter samples by.
        body: Optional request body containing text embedding.

    Returns:
        A list of filtered samples.
    """
    return sample_resolver.get_all_by_dataset_id(
        session=session,
        dataset_id=dataset_id,
        pagination=body.pagination,
        filters=body.filters,
        text_embedding=body.text_embedding,
        sample_ids=body.sample_ids,
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
    return sample_resolver.get_dimension_bounds(
        session=session,
        dataset_id=dataset.dataset_id,
        annotation_label_ids=annotation_label_ids,
    )


@samples_router.get("/samples/{sample_id}", response_model=SampleView)
def read_sample(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    sample_id: Annotated[UUID, Path(title="Sample Id")],
) -> SampleTable:
    """Retrieve a single sample from the database."""
    sample = sample_resolver.get_by_id(session=session, dataset_id=dataset_id, sample_id=sample_id)
    if not sample:
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")
    return sample


@samples_router.put("/samples/{sample_id}")
def update_sample(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Sample Id")],
    sample_input: SampleCreate,
) -> SampleTable:
    """Update an existing sample in the database."""
    sample = sample_resolver.update(session=session, sample_id=sample_id, sample_data=sample_input)
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
    if not sample_resolver.delete(session=session, dataset_id=dataset_id, sample_id=sample_id):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail="Sample not found")
    return {"status": "deleted"}


@samples_router.post(
    "/samples/{sample_id}/tag/{tag_id}",
    status_code=HTTP_STATUS_CREATED,
)
def add_tag_to_sample(
    session: SessionDep,
    sample_id: UUID,
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    tag_id: UUID,
) -> bool:
    """Add sample to a tag."""
    sample = sample_resolver.get_by_id(session=session, dataset_id=dataset_id, sample_id=sample_id)
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
    dataset_id: Annotated[UUID, Path(title="Dataset Id", description="The ID of the dataset")],
    sample_id: UUID,
) -> bool:
    """Remove sample from a tag."""
    sample = sample_resolver.get_by_id(session=session, dataset_id=dataset_id, sample_id=sample_id)
    if not sample:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Sample {sample_id} not found",
        )

    if not tag_resolver.remove_tag_from_sample(session=session, tag_id=tag_id, sample=sample):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=f"Tag {tag_id} not found")

    return True


class SampleAdjacentsParams(BaseModel):
    """Parameters for getting adjacent samples."""

    filters: SampleFilter | None = None
    text_embedding: list[float] | None = None
