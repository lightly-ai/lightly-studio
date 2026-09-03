"""Routes for bulk-creating classification annotations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Path
from fastapi.params import Body
from pydantic import BaseModel

from lightly_studio.api.routes.api.status import HTTP_STATUS_CREATED
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.resolvers.grid_filter import GridFilter
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.create_classification_annotations import (
    ClassificationAnnotationsCreated,
)

create_classification_annotations_router = APIRouter()


class ClassificationAnnotationsBulkInput(BaseModel):
    """API interface to create one classification annotation per listed sample.

    If annotation_collection_name is None, a default name is set.
    """

    sample_ids: list[UUID]
    class_name: str
    annotation_collection_name: str | None = None


class ClassificationAnnotationsBulkByFilterInput(BaseModel):
    """API interface to create one classification annotation per matched sample.

    The caller must supply a filter to determine the sample type. The filter itself
    can have no conditions, e.g. ``{"filter_type": "image"}``.
    If annotation_collection_name is None, a default name is set.
    """

    filter: GridFilter
    class_name: str
    annotation_collection_name: str | None = None


@create_classification_annotations_router.post(
    "/annotations/classifications/bulk",
    status_code=HTTP_STATUS_CREATED,
)
def create_classification_annotations(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    body: Annotated[ClassificationAnnotationsBulkInput, Body()],
) -> ClassificationAnnotationsCreated:
    """Create a classification annotation on each of the given samples.

    Samples that already have the annotation class are reported as skipped. Other
    annotation classes on a sample are kept.
    """
    return annotations_service.create_classification_annotations(
        session=session,
        collection_id=collection_id,
        class_name=body.class_name,
        sample_ids=body.sample_ids,
        annotation_collection_name=body.annotation_collection_name,
    )


@create_classification_annotations_router.post(
    "/annotations/classifications/bulk_by_filter",
    status_code=HTTP_STATUS_CREATED,
)
def create_classification_annotations_by_filter(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    body: Annotated[ClassificationAnnotationsBulkByFilterInput, Body()],
) -> ClassificationAnnotationsCreated:
    """Create a classification annotation on every sample the filter matches.

    Behaves like the bulk route, but resolves the samples server-side.
    """
    return annotations_service.create_classification_annotations_by_filter(
        session=session,
        collection_id=collection_id,
        class_name=body.class_name,
        grid_filter=body.filter,
        annotation_collection_name=body.annotation_collection_name,
    )
