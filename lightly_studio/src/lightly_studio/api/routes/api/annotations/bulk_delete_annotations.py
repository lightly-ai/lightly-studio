"""Bulk delete annotation routes."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.params import Body
from pydantic import BaseModel, Field
from sqlmodel import Session, col, select

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database import db_array
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import NotFoundError
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import (
    annotation_resolver,
    evaluation_run_resolver,
    grid_filter_sample_ids,
)
from lightly_studio.resolvers.grid_filter import GridFilter

bulk_delete_annotations_router = APIRouter()


class BulkDeleteAnnotationsInput(BaseModel):
    """API input for bulk annotation deletion."""

    annotation_ids: list[UUID] = Field(min_length=1)


class BulkDeleteAnnotationsByFilterInput(BaseModel):
    """API input for filtered bulk annotation deletion."""

    filter: GridFilter


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

    Raises:
        NotFoundError: If an annotation is not in the collection. Nothing is deleted then.
    """
    annotation_ids = set(body.annotation_ids)
    found_ids = _get_annotation_ids_in_collection(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=list(annotation_ids),
    )
    missing_count = len(annotation_ids - found_ids)
    if missing_count > 0:
        raise NotFoundError(
            f"{missing_count} annotations not found in collection {collection.collection_id}."
        )
    return _delete_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=list(found_ids),
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
    return _delete_annotations(
        session=session,
        collection_id=collection.collection_id,
        annotation_ids=session.exec(annotation_ids_query).all(),
    )


def _get_annotation_ids_in_collection(
    session: Session, collection_id: UUID, annotation_ids: Sequence[UUID]
) -> set[UUID]:
    query = (
        select(AnnotationBaseTable.sample_id)
        .join(AnnotationBaseTable.sample)
        .where(SampleTable.collection_id == collection_id)
        .where(db_array.in_array(column=col(AnnotationBaseTable.sample_id), values=annotation_ids))
    )
    return set(session.exec(query).all())


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
