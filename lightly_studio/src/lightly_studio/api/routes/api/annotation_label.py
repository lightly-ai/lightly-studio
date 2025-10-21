"""This module contains the API routes for managing annotation labels."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException

from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation_label import (
    AnnotationLabelCreate,
    AnnotationLabelTable,
)
from lightly_studio.resolvers import annotation_label_resolver

annotations_label_router = APIRouter()


@annotations_label_router.post(
    "/annotation_labels",
    status_code=HTTP_STATUS_CREATED,
)
def create_annotation_label(
    input_label: AnnotationLabelCreate,
    session: SessionDep,
) -> AnnotationLabelTable:
    """Create a new annotation label in the database."""
    return annotation_label_resolver.create(session=session, label=input_label)


@annotations_label_router.get("/annotation_labels")
def read_annotation_labels(
    session: SessionDep,
) -> list[AnnotationLabelTable]:
    """Retrieve a list of annotation labels from the database."""
    return annotation_label_resolver.get_all(session=session)


@annotations_label_router.get("/annotation_labels/{label_id}")
def read_annotation_label(
    label_id: UUID,
    session: SessionDep,
) -> AnnotationLabelTable:
    """Retrieve a single annotation label from the database."""
    label = annotation_label_resolver.get_by_id(session=session, label_id=label_id)
    if not label:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Annotation label not found",
        )
    return label


@annotations_label_router.put("/annotation_labels/{label_id}")
def update_annotation_label(
    label_id: UUID,
    label_input: AnnotationLabelCreate,
    session: SessionDep,
) -> AnnotationLabelTable:
    """Update an existing annotation label in the database."""
    label = annotation_label_resolver.update(
        session=session, label_id=label_id, label_data=label_input
    )
    if not label:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Annotation label not found",
        )
    return label


@annotations_label_router.delete("/annotation_labels/{label_id}")
def delete_annotation_label(
    label_id: UUID,
    session: SessionDep,
) -> dict[str, str]:
    """Delete an annotation label from the database."""
    if not annotation_label_resolver.delete(session=session, label_id=label_id):
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Annotation label not found",
        )
    return {"status": "deleted"}
