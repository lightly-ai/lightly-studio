"""Bulk delete annotation routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.params import Body
from pydantic import BaseModel

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.services import annotations_service

delete_annotations_router = APIRouter()


class DeleteAnnotationsInput(BaseModel):
    """API input for bulk annotation deletion."""

    annotation_ids: list[UUID]


class DeleteAnnotationsResult(BaseModel):
    """API result of bulk annotation deletion."""

    deleted_count: int


@delete_annotations_router.delete(
    "/annotations",
    response_model=DeleteAnnotationsResult,
)
def delete_annotations(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[DeleteAnnotationsInput, Body()],
) -> DeleteAnnotationsResult:
    """Delete the given annotations of an annotation collection."""
    deleted_count = annotations_service.delete_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=body.annotation_ids,
    )
    return DeleteAnnotationsResult(deleted_count=deleted_count)
