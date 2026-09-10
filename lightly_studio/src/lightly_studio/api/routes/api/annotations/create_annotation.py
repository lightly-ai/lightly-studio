"""Create annotation route."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi.params import Body
from pydantic import BaseModel
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import HTTP_STATUS_CREATED
from lightly_studio.database import db_array
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationType,
    AnnotationView,
)
from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import annotation_resolver, grid_filter_sample_ids
from lightly_studio.resolvers.annotation_resolver.bulk_create_classifications import (
    BulkCreateClassificationsResult,
)
from lightly_studio.resolvers.grid_filter import GridFilter
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_annotation import AnnotationCreateParams

create_annotation_router = APIRouter()


class AnnotationCreateInput(BaseModel):
    """API interface to create annotation.

    If annotation_collection_name is None, a default name is set.
    """

    annotation_label_id: UUID
    annotation_type: AnnotationType
    annotation_collection_name: str | None = None
    parent_sample_id: UUID
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    segmentation_mask: list[int] | None = None
    start_time_s: float | None = None
    end_time_s: float | None = None


class BulkCreateClassificationsInput(BaseModel):
    """API input for bulk classification creation."""

    sample_ids: list[UUID]
    class_name: str
    annotation_collection_name: str | None = None


class BulkCreateClassificationsByFilterInput(BaseModel):
    """API input for filtered bulk classification creation."""

    filter: GridFilter
    class_name: str
    annotation_collection_name: str | None = None


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


@create_annotation_router.post(
    "/annotations/classifications/bulk_create",
    response_model=BulkCreateClassificationsResult,
    status_code=HTTP_STATUS_CREATED,
)
def bulk_create_classifications(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[BulkCreateClassificationsInput, Body()],
) -> BulkCreateClassificationsResult:
    """Bulk-create classification annotations for selected samples."""
    return annotation_resolver.bulk_create_classifications(
        session=session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids_query=_build_sample_ids_query(
            collection_id=collection.collection_id,
            sample_ids=body.sample_ids,
        ),
        class_name=body.class_name,
        annotation_collection_name=body.annotation_collection_name,
    )


@create_annotation_router.post(
    "/annotations/classifications/bulk_create_by_filter",
    response_model=BulkCreateClassificationsResult,
    status_code=HTTP_STATUS_CREATED,
)
def bulk_create_classifications_by_filter(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: Annotated[BulkCreateClassificationsByFilterInput, Body()],
) -> BulkCreateClassificationsResult:
    """Bulk-create classification annotations for filtered samples."""
    return annotation_resolver.bulk_create_classifications(
        session=session,
        parent_collection_id=collection.collection_id,
        parent_sample_ids_query=grid_filter_sample_ids.build_sample_ids_query(
            session=session,
            collection_id=collection.collection_id,
            grid_filter=body.filter,
        ),
        class_name=body.class_name,
        annotation_collection_name=body.annotation_collection_name,
    )


def _build_sample_ids_query(
    collection_id: UUID,
    sample_ids: Sequence[UUID],
) -> SelectOfScalar[UUID]:
    return (
        select(SampleTable.sample_id)
        .where(SampleTable.collection_id == collection_id)
        .where(db_array.in_array(column=col(SampleTable.sample_id), values=sample_ids))
    )
