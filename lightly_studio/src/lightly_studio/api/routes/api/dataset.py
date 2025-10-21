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
from lightly_studio.models.dataset import (
    DatasetCreate,
    DatasetTable,
    DatasetView,
)
from lightly_studio.resolvers import dataset_resolver
from lightly_studio.resolvers.dataset_resolver import (
    ExportFilter,
)

dataset_router = APIRouter()


def get_and_validate_dataset_id(
    session: SessionDep,
    dataset_id: UUID,
) -> DatasetTable:
    """Get and validate the existence of a dataset on a route."""
    dataset = dataset_resolver.get_by_id(session=session, dataset_id=dataset_id)
    if not dataset:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f""" Dataset with {dataset_id} not found.""",
        )
    return dataset


@dataset_router.post(
    "/datasets",
    response_model=DatasetView,
    status_code=201,
)
def create_dataset(
    dataset_input: DatasetCreate,
    session: SessionDep,
) -> DatasetTable:
    """Create a new dataset in the database."""
    return dataset_resolver.create(session=session, dataset=dataset_input)


@dataset_router.get("/datasets", response_model=List[DatasetView])
def read_datasets(
    session: SessionDep,
    paginated: Annotated[Paginated, Query()],
) -> list[DatasetTable]:
    """Retrieve a list of datasets from the database."""
    return dataset_resolver.get_all(session=session, offset=paginated.offset, limit=paginated.limit)


@dataset_router.get("/datasets/{dataset_id}")
def read_dataset(
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
) -> DatasetTable:
    """Retrieve a single dataset from the database."""
    return dataset


@dataset_router.put("/datasets/{dataset_id}")
def update_dataset(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
    dataset_input: DatasetCreate,
) -> DatasetTable:
    """Update an existing dataset in the database."""
    return dataset_resolver.update(
        session=session,
        dataset_id=dataset.dataset_id,
        dataset_data=dataset_input,
    )


@dataset_router.delete("/datasets/{dataset_id}")
def delete_dataset(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
) -> dict[str, str]:
    """Delete a dataset from the database."""
    dataset_resolver.delete(session=session, dataset_id=dataset.dataset_id)
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
@dataset_router.post(
    "/datasets/{dataset_id}/export",
)
def export_dataset_to_absolute_paths(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
    body: ExportBody,
) -> PlainTextResponse:
    """Export dataset from the database."""
    # export dataset to absolute paths
    exported = dataset_resolver.export(
        session=session,
        dataset_id=dataset.dataset_id,
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
@dataset_router.post(
    "/datasets/{dataset_id}/export/stats",
)
def export_dataset_stats(
    session: SessionDep,
    dataset: Annotated[
        DatasetTable,
        Path(title="Dataset Id"),
        Depends(get_and_validate_dataset_id),
    ],
    body: ExportBody,
) -> int:
    """Get statistics about the export query."""
    return dataset_resolver.get_filtered_samples_count(
        session=session,
        dataset_id=dataset.dataset_id,
        include=body.include,
        exclude=body.exclude,
    )
