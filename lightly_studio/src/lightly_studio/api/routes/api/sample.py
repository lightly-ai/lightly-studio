"""This module contains the API routes for managing samples."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.sample import SampleViewsWithCount
from lightly_studio.resolvers import (
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver.get_filtered_samples import SamplesWithCount
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

sample_router = APIRouter(tags=["sample"])


class ReadSamplesRequest(BaseModel):
    """Request body for reading samples."""

    filters: SampleFilter = Field(description="Filter parameters for samples")


@sample_router.post("/samples/list", response_model=SampleViewsWithCount)
def read_samples(
    session: SessionDep,
    body: ReadSamplesRequest,
    pagination: Annotated[PaginatedWithCursor, Depends()],
) -> SamplesWithCount:
    """Retrieve a list of samples from the database with optional filtering.

    Args:
        session: The database session.
        body: Optional request body containing filters.
        pagination: Pagination parameters (cursor and limit).

    Returns:
        A list of filtered samples.
    """
    if body.filters.collection_id is None:
        raise ValueError("Collection ID must be provided in filters.")
    return sample_resolver.get_filtered_samples(
        session=session,
        filters=body.filters,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
    )


@sample_router.post(
    "/collections/{collection_id}/samples/{sample_id}/tag/{tag_id}",
    status_code=HTTP_STATUS_CREATED,
)
def add_tag_to_sample(
    session: SessionDep,
    sample_id: UUID,
    # TODO(Michal, 10/2025): Remove unused collection_id.
    collection_id: Annotated[  # noqa: ARG001
        UUID, Path(title="Collection Id", description="The ID of the collection")
    ],
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


@sample_router.delete("/collections/{collection_id}/samples/{sample_id}/tag/{tag_id}")
def remove_tag_from_sample(
    session: SessionDep,
    tag_id: UUID,
    # TODO(Michal, 10/2025): Remove unused collection_id.
    collection_id: Annotated[  # noqa: ARG001
        UUID, Path(title="Collection Id", description="The ID of the collection")
    ],
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
