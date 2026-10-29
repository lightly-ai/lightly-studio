"""Annotation source routes."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Path
from pydantic import BaseModel, Field

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

    Responds with 409 if evaluation runs use the annotation source.
    """
    deleted_count = annotation_source_service.delete_annotation_source(
        session=session,
        dataset_collection_id=collection_id,
        annotation_source_id=annotation_collection_id,
    )
    return DeleteAnnotationSourceResult(deleted_annotation_count=deleted_count)


class RenameAnnotationSourceInput(BaseModel):
    """API input for renaming an annotation source."""

    name: str = Field(min_length=1)


class RenameAnnotationSourceResult(BaseModel):
    """Result of an annotation source rename. The renamed source has a new ID."""

    annotation_collection_id: UUID


@annotation_sources_router.put(
    "/annotation_collections/{annotation_collection_id}",
    response_model=RenameAnnotationSourceResult,
)
def rename_annotation_source(
    session: SessionDep,
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The collection that owns the source")
    ],
    annotation_collection_id: Annotated[
        UUID, Path(title="annotation collection Id", description="The source to rename")
    ],
    body: Annotated[RenameAnnotationSourceInput, Body()],
) -> RenameAnnotationSourceResult:
    """Rename an annotation source.

    Responds with 400 if another source has the name and 409 if evaluation runs use the source.
    """
    renamed_id = annotation_source_service.rename_annotation_source(
        session=session,
        dataset_collection_id=collection_id,
        annotation_source_id=annotation_collection_id,
        name=body.name.strip(),
    )
    return RenameAnnotationSourceResult(annotation_collection_id=renamed_id)


class MoveAnnotationsInput(BaseModel):
    """API input for moving annotations to another annotation source."""

    annotation_ids: list[UUID] = Field(min_length=1)
    target_annotation_collection_name: str = Field(min_length=1)


class MoveAnnotationsResult(BaseModel):
    """Result of an annotation move."""

    annotation_collection_id: UUID
    moved_count: int


@annotation_sources_router.post(
    "/annotations/move_to_source",
    response_model=MoveAnnotationsResult,
)
def move_annotations(
    session: SessionDep,
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The collection that owns the sources")
    ],
    body: Annotated[MoveAnnotationsInput, Body()],
) -> MoveAnnotationsResult:
    """Move annotations to an annotation source, creating the source if it does not exist."""
    target_id, moved_count = annotation_source_service.move_annotations(
        session=session,
        dataset_collection_id=collection_id,
        annotation_ids=body.annotation_ids,
        target_annotation_source_name=body.target_annotation_collection_name.strip(),
    )
    return MoveAnnotationsResult(annotation_collection_id=target_id, moved_count=moved_count)
