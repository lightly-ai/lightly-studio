"""This module contains the API routes for splitting a collection into tags."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_UNPROCESSABLE_ENTITY,
)
from lightly_studio.core.dataset_query import random_split
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.grid_filter import GridFilter

split_router = APIRouter()


class SplitCreateBody(BaseModel):
    """Body for splitting a collection into named split tags.

    ``filter`` reuses the same grid filter payload the images grid sends. When it
    is omitted, the whole collection is split.
    """

    sizes: dict[str, float] = Field(description="Split name to percentage, summing to 100.")
    filter: GridFilter | None = None
    seed: int | None = Field(default=None, description="Optional seed for a reproducible split.")


class SplitCountView(BaseModel):
    """The number of samples assigned to a single split."""

    name: str
    count: int


class SplitResultView(BaseModel):
    """Response model summarizing a completed split."""

    splits: list[SplitCountView]
    seed: int


@split_router.post(
    "/collections/{collection_id}/splits",
    response_model=SplitResultView,
    status_code=HTTP_STATUS_CREATED,
)
def create_split(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    body: SplitCreateBody,
) -> SplitResultView:
    """Randomly split the collection (or a filtered subset) into named split tags."""
    collection_id = collection.collection_id
    sample_ids = _resolve_sample_ids(
        session=session, collection_id=collection_id, grid_filter=body.filter
    )
    try:
        result = random_split.random_split(
            session=session,
            collection_id=collection_id,
            sample_ids=sample_ids,
            sizes=body.sizes,
            seed=body.seed,
        )
    except ValueError as e:
        raise HTTPException(status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY, detail=str(e)) from e

    splits = [SplitCountView(name=name, count=count) for name, count in result.counts.items()]
    return SplitResultView(splits=splits, seed=result.seed)


def _resolve_sample_ids(
    session: Session, collection_id: UUID, grid_filter: GridFilter | None
) -> list[UUID]:
    """Resolve the input sample ids, using the filter or the whole collection."""
    if grid_filter is not None:
        query = grid_filter.build_sample_ids_query(collection_id=collection_id)
    else:
        query = select(SampleTable.sample_id).where(col(SampleTable.collection_id) == collection_id)
    return [sample_id for sample_id in session.exec(query).all() if sample_id is not None]
