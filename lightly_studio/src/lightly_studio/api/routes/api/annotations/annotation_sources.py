"""Annotation source routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from pydantic import BaseModel

from lightly_studio.database.db_manager import SessionDep
from lightly_studio.services import annotation_source_service

annotation_sources_router = APIRouter()


class DeleteAnnotationSourceResult(BaseModel):
    """Result of an annotation source delete."""

    deleted_annotation_count: int


@annotation_sources_router.delete(
    "/annotation_collections/{annotation_collection_id}",
    response_model=DeleteAnnotationSourceResult,
)
def delete_annotation_source(
    session: SessionDep,
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The collection that owns the source")
    ],
    annotation_collection_id: Annotated[
        UUID, Path(title="annotation collection Id", description="The source to delete")
    ],
) -> DeleteAnnotationSourceResult:
    """Delete an annotation source and all its annotations.

    Responds with 409 if evaluation runs, export jobs or child collections use the annotation
    source.
    """
    deleted_count = annotation_source_service.delete_annotation_source(
        session=session,
        dataset_collection_id=collection_id,
        annotation_source_id=annotation_collection_id,
    )
    return DeleteAnnotationSourceResult(deleted_annotation_count=deleted_count)
