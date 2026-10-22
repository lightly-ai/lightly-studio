"""Bulk delete annotation routes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from fastapi.params import Body
from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.resolvers import annotation_resolver, evaluation_run_resolver, sample_resolver

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
    return _delete_annotations(session=session, annotation_ids=body.annotation_ids)


def _delete_annotations(
    session: Session, annotation_ids: Sequence[UUID]
) -> BulkDeleteAnnotationsResult:
    """Delete annotations and mark the evaluation runs of their collections stale."""
    annotation_collection_ids = {
        sample.collection_id
        for sample in sample_resolver.get_many_by_id(
            session=session, sample_ids=list(annotation_ids)
        )
    }
    deleted_count = annotation_resolver.delete_annotations_by_ids(
        session=session, annotation_ids=annotation_ids
    )
    for annotation_collection_id in annotation_collection_ids:
        evaluation_run_resolver.mark_stale_by_collection_id(
            session=session, collection_id=annotation_collection_id
        )
    return BulkDeleteAnnotationsResult(deleted_count=deleted_count)
