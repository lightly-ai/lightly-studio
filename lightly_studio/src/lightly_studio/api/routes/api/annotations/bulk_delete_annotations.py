"""Bulk delete annotation routes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.params import Body
from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver

bulk_delete_annotations_router = APIRouter()


class BulkDeleteAnnotationsInput(BaseModel):
    """API input for bulk annotation deletion."""

    annotation_ids: list[UUID] = Field(min_length=1)


class BulkDeleteAnnotationsResult(BaseModel):
    """Result of a bulk annotation deletion."""

    deleted_count: int


@bulk_delete_annotations_router.post(
    "/annotations/bulk_delete",
    response_model=BulkDeleteAnnotationsResult,
)
def bulk_delete_annotations(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[BulkDeleteAnnotationsInput, Body()],
) -> BulkDeleteAnnotationsResult:
    """Delete the given annotations of an annotation collection.

    IDs that do not exist are ignored.
    """
    return _delete_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=body.annotation_ids,
    )


def _delete_annotations(
    session: Session, collection_id: UUID, annotation_ids: Sequence[UUID]
) -> BulkDeleteAnnotationsResult:
    """Delete annotations of one annotation collection and mark its evaluation runs stale."""
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=annotation_ids
    )
    if deleted_count > 0:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=collection_id
        )
    return BulkDeleteAnnotationsResult(deleted_count=deleted_count)
