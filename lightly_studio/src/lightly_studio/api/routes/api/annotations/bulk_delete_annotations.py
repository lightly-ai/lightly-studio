"""Bulk delete annotation routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.params import Body
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import grid_filter_sample_ids
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.services import annotations_service

bulk_delete_annotations_router = APIRouter()


class BulkDeleteAnnotationsInput(BaseModel):
    """API input for bulk annotation deletion."""

    annotation_ids: list[UUID] = Field(min_length=1)


class BulkDeleteAnnotationsByFilterInput(BaseModel):
    """API input for filtered bulk annotation deletion."""

    filter: AnnotationsFilter


class BulkDeleteAnnotationsResult(BaseModel):
    """Result of a bulk annotation deletion."""

    deleted_count: int


@bulk_delete_annotations_router.post(
    "/annotations/bulk_delete",
    response_model=BulkDeleteAnnotationsResult,
)
def bulk_delete_annotations(
    # The path prefix has collection_id, the generator needs it as a parameter
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    session: SessionDep,
    body: Annotated[BulkDeleteAnnotationsInput, Body()],
) -> BulkDeleteAnnotationsResult:
    """Delete the given annotations.

    IDs that do not exist are ignored.
    """
    return BulkDeleteAnnotationsResult(
        deleted_count=annotations_service.delete_annotations_by_ids(
            session=session, annotation_ids=body.annotation_ids
        )
    )


@bulk_delete_annotations_router.post(
    "/annotations/bulk_delete_by_filter",
    response_model=BulkDeleteAnnotationsResult,
)
def bulk_delete_annotations_by_filter(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[BulkDeleteAnnotationsByFilterInput, Body()],
) -> BulkDeleteAnnotationsResult:
    """Delete the annotations of an annotation collection that match a filter."""
    annotation_ids_query = grid_filter_sample_ids.build_sample_ids_query(
        session=session,
        collection_id=collection.collection_id,
        grid_filter=body.filter,
    )
    return BulkDeleteAnnotationsResult(
        deleted_count=annotations_service.delete_annotations_by_ids(
            session=session, annotation_ids=session.exec(annotation_ids_query).all()
        )
    )
