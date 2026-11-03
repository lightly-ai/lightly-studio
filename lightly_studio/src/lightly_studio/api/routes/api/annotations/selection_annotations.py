"""Routes that act on a selection of images or annotations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Path
from fastapi.params import Body
from pydantic import BaseModel
from sqlmodel import col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.api.routes.api.annotations.bulk_delete_annotations import (
    BulkDeleteAnnotationsResult,
)
from lightly_studio.api.routes.api.status import HTTP_STATUS_UNPROCESSABLE_ENTITY
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_resolver, grid_filter_sample_ids
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.grid_filter import GridFilter

selection_annotations_router = APIRouter()


class DeleteClassificationsForSamplesInput(BaseModel):
    """API input for deleting the classifications of a selection of samples.

    Send either explicit ``sample_ids`` or a ``filter`` that selects the samples.
    """

    sample_ids: list[UUID] | None = None
    filter: GridFilter | None = None
    annotation_label_id: UUID
    annotation_collection_id: UUID


class AnnotationLabelCountsInput(BaseModel):
    """API input for counting the annotation classes of a selection."""

    filter: AnnotationsFilter


class AnnotationLabelCountView(BaseModel):
    """Number of selected annotations that have an annotation class."""

    annotation_label_id: UUID
    label_name: str
    count: int


@selection_annotations_router.post(
    "/annotations/classifications/delete_for_samples",
    response_model=BulkDeleteAnnotationsResult,
)
def delete_for_samples(
    collection_id: Annotated[
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    session: SessionDep,
    body: Annotated[DeleteClassificationsForSamplesInput, Body()],
) -> BulkDeleteAnnotationsResult:
    """Delete one classification, in one annotation source, from a selection of samples."""
    if body.sample_ids is not None:
        sample_ids_query = select(SampleTable.sample_id).where(
            col(SampleTable.sample_id).in_(body.sample_ids)
        )
    elif body.filter is not None:
        sample_ids_query = grid_filter_sample_ids.build_sample_ids_query(
            session=session, collection_id=collection_id, grid_filter=body.filter
        )
    else:
        raise HTTPException(
            status_code=HTTP_STATUS_UNPROCESSABLE_ENTITY,
            detail="Either sample_ids or filter is required.",
        )
    annotation_ids_query = _select_classification_ids(
        sample_ids_query=sample_ids_query,
        annotation_label_id=body.annotation_label_id,
        annotation_collection_id=body.annotation_collection_id,
    )
    return BulkDeleteAnnotationsResult(
        deleted_count=annotation_resolver.delete_annotations_by_ids(
            session=session, annotation_ids=session.exec(annotation_ids_query).all()
        )
    )


@selection_annotations_router.post(
    "/annotations/label_counts",
    response_model=list[AnnotationLabelCountView],
)
def label_counts(
    # The path prefix has collection_id, the generator needs it as a parameter
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    session: SessionDep,
    body: Annotated[AnnotationLabelCountsInput, Body()],
) -> list[AnnotationLabelCountView]:
    """Count the annotations a filter matches, grouped by annotation class."""
    annotation_ids_query = body.filter.apply(
        select(AnnotationBaseTable.sample_id).join(AnnotationBaseTable.sample)
    )
    query = (
        select(
            AnnotationBaseTable.annotation_label_id,
            AnnotationLabelTable.annotation_label_name,
            func.count().label("count"),
        )
        .select_from(AnnotationBaseTable)
        .join(
            AnnotationLabelTable,
            col(AnnotationLabelTable.annotation_label_id)
            == col(AnnotationBaseTable.annotation_label_id),
        )
        .where(col(AnnotationBaseTable.sample_id).in_(annotation_ids_query))
        .group_by(
            col(AnnotationBaseTable.annotation_label_id),
            col(AnnotationLabelTable.annotation_label_name),
        )
        .order_by(func.count().desc(), col(AnnotationLabelTable.annotation_label_name))
    )
    rows = session.exec(query).all()
    return [
        AnnotationLabelCountView(annotation_label_id=label_id, label_name=name, count=count)
        for label_id, name, count in rows
    ]


def _select_classification_ids(
    sample_ids_query: SelectOfScalar[UUID],
    annotation_label_id: UUID,
    annotation_collection_id: UUID,
) -> SelectOfScalar[UUID]:
    return (
        select(AnnotationBaseTable.sample_id)
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .where(
            col(AnnotationBaseTable.parent_sample_id).in_(sample_ids_query),
            col(AnnotationBaseTable.annotation_type) == AnnotationType.CLASSIFICATION,
            col(AnnotationBaseTable.annotation_label_id) == annotation_label_id,
            col(SampleTable.collection_id) == annotation_collection_id,
        )
    )
