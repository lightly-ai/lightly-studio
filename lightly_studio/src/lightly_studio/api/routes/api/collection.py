"""This module contains the API routes for managing datasets."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlmodel import Field
from typing_extensions import Annotated

from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import (
    CollectionCreate,
    CollectionOverviewView,
    CollectionTable,
    CollectionView,
    CollectionViewWithCount,
)
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.collection_resolver.export import ExportFilter

collection_router = APIRouter()


def get_and_validate_collection_id(
    session: SessionDep,
    dataset_id: UUID,
) -> CollectionTable:
    """Get and validate the existence of a dataset on a route."""
    collection = collection_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if not collection:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f""" Collection with {dataset_id} not found.""",
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


@collection_router.get("/collections/{dataset_id}/dataset", response_model=CollectionView)
def read_dataset(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Dataset Id")],
) -> CollectionTable:
    """Retrieve the root dataset for a given dataset."""
    return collection_resolver.get_dataset(session=session, dataset_id=dataset_id)


@collection_router.get("/collections/{dataset_id}/hierarchy", response_model=List[CollectionView])
def read_collection_hierarchy(
    session: SessionDep,
    dataset_id: Annotated[UUID, Path(title="Root Dataset Id")],
) -> list[CollectionTable]:
    """Retrieve the collection hierarchy from the database, starting with the root node."""
    return collection_resolver.get_hierarchy(session=session, root_dataset_id=dataset_id)


@collection_router.get("/collections/overview", response_model=List[CollectionOverviewView])
def read_datasets_overview(session: SessionDep) -> list[CollectionOverviewView]:
    """Retrieve datasets with metadata for dashboard display."""
    return collection_resolver.get_datasets_overview(session=session)


@collection_router.get("/collections/{dataset_id}", response_model=CollectionViewWithCount)
def read_collection(
    session: SessionDep,
    dataset: Annotated[
        CollectionTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> CollectionViewWithCount:
    """Retrieve a single collection from the database."""
    return collection_resolver.get_collection_details(session=session, dataset=dataset)


@collection_router.put("/collections/{dataset_id}")
def update_collection(
    session: SessionDep,
    dataset: Annotated[
        CollectionTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_collection_id),
    ],
    collection_input: CollectionCreate,
) -> CollectionTable:
    """Update an existing collection in the database."""
    return collection_resolver.update(
        session=session,
        dataset_id=dataset.collection_id,
        collection_input=collection_input,
    )


@collection_router.delete("/collections/{dataset_id}")
def delete_collection(
    session: SessionDep,
    dataset: Annotated[
        CollectionTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> dict[str, str]:
    """Delete a collection from the database."""
    collection_resolver.delete(session=session, dataset_id=dataset.collection_id)
    return {"status": "deleted"}


# TODO(Michal, 09/2025): Move to export.py
class ExportBody(BaseModel):
    """body parameters for including or excluding tag_ids or sample_ids."""

    include: ExportFilter | None = Field(
        None, description="include filter for sample_ids or tag_ids"
    )
    exclude: ExportFilter | None = Field(
        None, description="exclude filter for sample_ids or tag_ids"
    )


# This endpoint should be a GET, however due to the potential huge size
# of sample_ids, it is a POST request to avoid URL length limitations.
# A body with a GET request is supported by fastAPI however it has undefined
# behavior: https://fastapi.tiangolo.com/tutorial/body/
# TODO(Michal, 09/2025): Move to export.py
@collection_router.post(
    "/collections/{dataset_id}/export",
)
def export_dataset_to_absolute_paths(
    session: SessionDep,
    dataset: Annotated[
        CollectionTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_collection_id),
    ],
    body: ExportBody,
) -> PlainTextResponse:
    """Export dataset from the database."""
    # export dataset to absolute paths
    exported = collection_resolver.export(
        session=session,
        dataset_id=dataset.collection_id,
        include=body.include,
        exclude=body.exclude,
    )

    # Create a response with the exported data
    response = PlainTextResponse("\n".join(exported))

    # Add the Content-Disposition header to force download
    filename = f"{dataset.name}_exported_{datetime.now(timezone.utc)}.txt"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"

    return response


# TODO(Michal, 09/2025): Move to export.py
@collection_router.post(
    "/collections/{dataset_id}/export/stats",
)
def export_dataset_stats(
    session: SessionDep,
    dataset: Annotated[
        CollectionTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_collection_id),
    ],
    body: ExportBody,
) -> int:
    """Get statistics about the export query."""
    return collection_resolver.get_filtered_samples_count(
        session=session,
        dataset_id=dataset.collection_id,
        include=body.include,
        exclude=body.exclude,
    )
