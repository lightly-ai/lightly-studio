"""This module contains the API routes for managing datasets."""

from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.dataset import get_and_validate_dataset_id
from lightly_studio.db_manager import SessionDep
from lightly_studio.metadata import compute_typicality
from lightly_studio.models.dataset import DatasetTable
from lightly_studio.models.metadata import MetadataInfoView
from lightly_studio.resolvers import embedding_model_resolver
from lightly_studio.resolvers.metadata_resolver.sample.get_metadata_info import (
    get_all_metadata_keys_and_schema,
)

metadata_router = APIRouter(prefix="/datasets/{dataset_id}", tags=["metadata"])


@metadata_router.get("/metadata/info", response_model=List[MetadataInfoView])
def get_metadata_info(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
) -> list[MetadataInfoView]:
    """Get all metadata keys and their schema for a dataset.

    Args:
        session: The database session.
        dataset_id: The ID of the dataset.

    Returns:
        List of metadata info objects with name, type, and optionally min/max values
        for numerical metadata types.
    """
    return get_all_metadata_keys_and_schema(session=session, dataset_id=dataset_id)


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
    dataset: Annotated[
        DatasetTable,
        Depends(get_and_validate_dataset_id),
    ],
    request: ComputeTypicalityRequest,
) -> None:
    """Compute typicality metadata for a dataset.

    Args:
        session: The database session.
        dataset: The dataset to compute typicality for.
        request: Request parameters including optional embedding model name
            and metadata field name.

    Returns:
        None (204 No Content on success).
    """
    embedding_model = embedding_model_resolver.get_by_name(
        session=session,
        dataset_id=dataset.dataset_id,
        embedding_model_name=request.embedding_model_name,
    )

    compute_typicality.compute_typicality_metadata(
        session=session,
        dataset_id=dataset.dataset_id,
        embedding_model_id=embedding_model.embedding_model_id,
        metadata_name=request.metadata_name,
    )
