"""Create annotation route."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Path
from fastapi.params import Body
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
    AnnotationView,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_annotation import AnnotationCreateParams

create_annotation_router = APIRouter()


class AnnotationCreateInput(BaseModel):
    """API interface to create annotation."""

    annotation_label_id: UUID
    annotation_type: AnnotationType
    parent_sample_id: UUID
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    segmentation_mask: list[int] | None = None


@create_annotation_router.post(
    "/annotations",
    response_model=AnnotationView,
)
def create_annotation(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    create_annotation_input: Annotated[AnnotationCreateInput, Body()],
) -> AnnotationBaseTable:
    """Create a new annotation."""
    return annotations_service.create_annotation(
        session=session,
        annotation=AnnotationCreateParams(
            collection_id=collection_id, **create_annotation_input.model_dump()
        ),
    )
