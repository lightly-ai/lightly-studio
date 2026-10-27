"""Bulk relabel annotation routes."""

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
from lightly_studio.resolvers import annotation_resolver, grid_filter_sample_ids
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import AnnotationUpdate

bulk_relabel_annotations_router = APIRouter()


class BulkRelabelAnnotationsInput(BaseModel):
    """API input for bulk annotation relabeling."""

    annotation_ids: list[UUID] = Field(min_length=1)
    label_name: str


class BulkRelabelAnnotationsByFilterInput(BaseModel):
    """API input for filtered bulk annotation relabeling."""

    filter: AnnotationsFilter
    label_name: str


class PreviousAnnotationLabel(BaseModel):
    """Label of an annotation before a bulk relabel."""

    annotation_id: UUID
    label_name: str


class BulkRelabelAnnotationsResult(BaseModel):
    """Result of a bulk annotation relabel."""

    previous_labels: list[PreviousAnnotationLabel]


@bulk_relabel_annotations_router.post(
    "/annotations/bulk_relabel",
    response_model=BulkRelabelAnnotationsResult,
)
def bulk_relabel_annotations(
    collection_id: Annotated[
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    session: SessionDep,
    body: Annotated[BulkRelabelAnnotationsInput, Body()],
) -> BulkRelabelAnnotationsResult:
    """Assign a label to the given annotations.

    IDs that do not exist are ignored.
    """
    return _relabel_annotations(
        session=session,
        collection_id=collection_id,
        annotation_ids=body.annotation_ids,
        label_name=body.label_name,
    )


@bulk_relabel_annotations_router.post(
    "/annotations/bulk_relabel_by_filter",
    response_model=BulkRelabelAnnotationsResult,
)
def bulk_relabel_annotations_by_filter(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[BulkRelabelAnnotationsByFilterInput, Body()],
) -> BulkRelabelAnnotationsResult:
    """Assign a label to the annotations of an annotation collection that match a filter."""
    annotation_ids_query = grid_filter_sample_ids.build_sample_ids_query(
        session=session,
        collection_id=collection.collection_id,
        grid_filter=body.filter,
    )
    return _relabel_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=session.exec(annotation_ids_query).all(),
        label_name=body.label_name,
    )


def _relabel_annotations(
    session: Session, collection_id: UUID, annotation_ids: Sequence[UUID], label_name: str
) -> BulkRelabelAnnotationsResult:
    """Relabel annotations and return their labels from before the change."""
    annotations = annotation_resolver.get_by_ids(session=session, annotation_ids=annotation_ids)
    previous_labels = [
        PreviousAnnotationLabel(
            annotation_id=annotation.sample_id,
            label_name=annotation.annotation_label.annotation_label_name,
        )
        for annotation in annotations
    ]
    annotations_service.update_annotations(
        session=session,
        annotation_updates=[
            AnnotationUpdate(
                annotation_id=previous_label.annotation_id,
                collection_id=collection_id,
                label_name=label_name,
            )
            for previous_label in previous_labels
        ],
    )
    return BulkRelabelAnnotationsResult(previous_labels=previous_labels)
