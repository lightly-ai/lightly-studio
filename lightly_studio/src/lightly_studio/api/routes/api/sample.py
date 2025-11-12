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
from lightly_studio.models.image import (
    ImageView,
    ImageViewsWithCount,
)
from lightly_studio.resolvers import (
    image_resolver,
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.image_filter import (
    ImageFilter,
)

sample_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["sample"])

@sample_router.post(
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


@sample_router.delete("/samples/{sample_id}/tag/{tag_id}")
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

