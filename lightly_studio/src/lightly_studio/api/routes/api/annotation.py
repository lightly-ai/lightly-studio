"""This module contains the API routes for managing annotations."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.params import Query
from pydantic import BaseModel
from typing_extensions import Annotated

from lightly_studio.api.routes.api import annotations as annotations_module
from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import (
    HTTP_STATUS_CREATED,
    HTTP_STATUS_NOT_FOUND,
)
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationDetailsWithPayloadView,
    AnnotationView,
    AnnotationViewsWithCount,
    AnnotationWithPayloadAndCountView,
)
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import annotation_resolver, tag_resolver
from lightly_studio.resolvers.annotation_resolver.get_all import (
    GetAllAnnotationsResult,
)
from lightly_studio.resolvers.annotation_resolver.update_bounding_box import BoundingBoxCoordinates
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from lightly_studio.services import annotations_service
from lightly_studio.services.annotations_service.update_annotation import (
    AnnotationUpdate,
)

annotations_router = APIRouter(prefix="/collections/{collection_id}", tags=["annotations"])
annotations_router.include_router(annotations_module.create_annotation_router)


class AnnotationQueryParamsModel(BaseModel):
    """Model for all annotation query parameters."""

    pagination: PaginatedWithCursor
    annotation_label_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None


def _get_annotation_query_params(
    pagination: Annotated[PaginatedWithCursor, Depends()],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
) -> AnnotationQueryParamsModel:
    return AnnotationQueryParamsModel(
        pagination=pagination,
        annotation_label_ids=annotation_label_ids,
        tag_ids=tag_ids,
    )


@annotations_router.get("/annotations/count")
def count_annotations_by_collection(  # noqa: PLR0913 // FIXME: refactor to use proper pydantic
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    filtered_labels: Annotated[list[str] | None, Query()] = None,
    min_width: Annotated[int | None, Query(ge=0)] = None,
    max_width: Annotated[int | None, Query(ge=0)] = None,
    min_height: Annotated[int | None, Query(ge=0)] = None,
    max_height: Annotated[int | None, Query(ge=0)] = None,
    tag_ids: list[UUID] | None = None,
) -> list[dict[str, str | int]]:
    """Get annotation counts for a specific collection.

    Returns a list of dictionaries with label name and count.
    """
    counts = annotation_resolver.count_annotations_by_collection(
        session=session,
        collection_id=collection.collection_id,
        filtered_labels=filtered_labels,
        min_width=min_width,
        max_width=max_width,
        min_height=min_height,
        max_height=max_height,
        tag_ids=tag_ids,
    )

    return [
        {
            "label_name": label_name,
            "current_count": current_count,
            "total_count": total_count,
        }
        for label_name, current_count, total_count in counts
    ]


@annotations_router.get(
    "/annotations",
    response_model=AnnotationViewsWithCount,
)
def read_annotations(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    pagination: Annotated[PaginatedWithCursor, Depends()],
    annotation_label_ids: Annotated[list[UUID] | None, Query()] = None,
    tag_ids: Annotated[list[UUID] | None, Query()] = None,
) -> GetAllAnnotationsResult:
    """Retrieve a list of annotations from the database."""
    return annotation_resolver.get_all(
        session=session,
        pagination=Paginated(
            offset=pagination.offset,
            limit=pagination.limit,
        ),
        filters=AnnotationsFilter(
            collection_ids=[collection_id],
            annotation_label_ids=annotation_label_ids,
            annotation_tag_ids=tag_ids,
        ),
    )


@annotations_router.get(
    "/annotations/payload",
)
def read_annotations_with_payload(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    params: Annotated[AnnotationQueryParamsModel, Depends(_get_annotation_query_params)],
) -> AnnotationWithPayloadAndCountView:
    """Retrieve a list of annotations along with the parent sample data from the database."""
    return annotation_resolver.get_all_with_payload(
        session=session,
        pagination=Paginated(
            offset=params.pagination.offset,
            limit=params.pagination.limit,
        ),
        filters=AnnotationsFilter(
            collection_ids=[collection_id],
            annotation_label_ids=params.annotation_label_ids,
            annotation_tag_ids=params.tag_ids,
        ),
        collection_id=collection_id,
    )


@annotations_router.post(
    "/annotations/{annotation_id}/tag/{tag_id}",
    status_code=HTTP_STATUS_CREATED,
)
def add_tag_to_annotation(
    session: SessionDep,
    annotation_id: UUID,
    tag_id: UUID,
) -> bool:
    """Add annotation to a tag."""
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Annotation {annotation_id} not found",
        )

    if not tag_resolver.add_tag_to_annotation(
        session=session, tag_id=tag_id, annotation=annotation
    ):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=f"Tag {tag_id} not found")

    return True


class AnnotationUpdateInput(BaseModel):
    """API input model for updating an annotation."""

    annotation_id: UUID
    collection_id: UUID
    label_name: str | None = None
    bounding_box: BoundingBoxCoordinates | None = None
    segmentation_mask: list[int] | None = None


@annotations_router.put("/annotations/{annotation_id}")
def update_annotation(
    session: SessionDep,
    collection_id: Annotated[
        UUID,
        Path(title="collection Id"),
    ],
    annotation_id: Annotated[
        UUID,
        Path(title="Annotation ID", description="ID of the annotation to update"),
    ],
    annotation_update_input: Annotated[AnnotationUpdateInput, Body()],
) -> AnnotationBaseTable:
    """Update an existing annotation in the database."""
    return annotations_service.update_annotation(
        session=session,
        annotation_update=AnnotationUpdate(
            annotation_id=annotation_id,
            collection_id=collection_id,
            label_name=annotation_update_input.label_name,
            bounding_box=annotation_update_input.bounding_box,
            segmentation_mask=annotation_update_input.segmentation_mask,
        ),
    )


@annotations_router.put(
    "/annotations",
)
def update_annotations(
    session: SessionDep,
    collection_id: Annotated[
        UUID,
        Path(title="collection Id"),
    ],
    annotation_update_inputs: Annotated[list[AnnotationUpdateInput], Body()],
) -> list[AnnotationBaseTable]:
    """Update multiple annotations in the database."""
    return annotations_service.update_annotations(
        session=session,
        annotation_updates=[
            AnnotationUpdate(
                annotation_id=annotation_update_input.annotation_id,
                collection_id=collection_id,
                label_name=annotation_update_input.label_name,
                bounding_box=annotation_update_input.bounding_box,
                segmentation_mask=annotation_update_input.segmentation_mask,
            )
            for annotation_update_input in annotation_update_inputs
        ],
    )


@annotations_router.get("/annotations/{annotation_id}", response_model=AnnotationView)
def get_annotation(
    session: SessionDep,
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],  # We need collection_id because otherwise the path would not match
    annotation_id: Annotated[UUID, Path(title="Annotation ID")],
) -> AnnotationBaseTable:
    """Retrieve an existing annotation from the database."""
    return annotations_service.get_annotation_by_id(session=session, annotation_id=annotation_id)


@annotations_router.delete("/annotations/{annotation_id}/tag/{tag_id}")
def remove_tag_from_annotation(
    session: SessionDep,
    tag_id: UUID,
    annotation_id: UUID,
) -> bool:
    """Remove annotation from a tag."""
    annotation = annotation_resolver.get_by_id(session=session, annotation_id=annotation_id)
    if not annotation:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail=f"Annotation {annotation_id} not found",
        )

    if not tag_resolver.remove_tag_from_annotation(
        session=session, tag_id=tag_id, annotation=annotation
    ):
        raise HTTPException(status_code=HTTP_STATUS_NOT_FOUND, detail=f"Tag {tag_id} not found")

    return True


@annotations_router.delete("/annotations/{annotation_id}")
def delete_annotation(
    session: SessionDep,
    # We need collection_id because generator doesn't include it
    # actuall path for this route is /collections/{collection_id}/annotations/{annotation_id}
    collection_id: Annotated[  # noqa: ARG001
        UUID,
        Path(title="collection Id", description="The ID of the collection"),
    ],
    annotation_id: Annotated[
        UUID, Path(title="Annotation ID", description="ID of the annotation to delete")
    ],
) -> dict[str, str]:
    """Delete an annotation from the database."""
    try:
        annotations_service.delete_annotation(session=session, annotation_id=annotation_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="Annotation not found",
        ) from e


@annotations_router.get("/annotations/payload/{sample_id}")
def get_annotation_with_payload(
    session: SessionDep,
    sample_id: Annotated[UUID, Path(title="Annotation ID")],
) -> AnnotationDetailsWithPayloadView | None:
    """Retrieve an existing annotation with payload from the database."""
    return annotation_resolver.get_by_id_with_payload(session=session, sample_id=sample_id)
