"""This module contains the API routes for managing annotations."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Path
from fastapi.params import Query
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api import annotations as annotations_module
from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.api.routes.api.status import HTTP_STATUS_NOT_FOUND
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import (
    AnnotationBaseTable,
    AnnotationDetailsWithPayloadView,
    AnnotationView,
    AnnotationViewsWithCount,
    AnnotationWithPayloadAndCountView,
)
from lightly_studio.models.collection import AnnotationCollectionView, CollectionTable
from lightly_studio.models.embedding_region import EmbeddingRegion
from lightly_studio.resolvers import (
    annotation_resolver,
    collection_resolver,
    embedding_model_resolver,
    sample_embedding_resolver,
)
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


@annotations_router.get(
    "/annotation_collections",
    response_model=list[AnnotationCollectionView],
)
def read_annotation_collections(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
) -> list[AnnotationCollectionView]:
    """List annotation collections under the given parent collection.

    Each entry includes the distinct annotation types it contains, so the GUI
    can filter sources to those compatible with a chosen evaluation task.
    """
    collections = collection_resolver.get_annotation_collections(
        session=session,
        parent_collection_id=collection.collection_id,
    )
    types_by_collection_id = collection_resolver.get_annotation_types_by_collection_ids(
        session=session,
        collection_ids=[c.collection_id for c in collections],
    )
    return [
        AnnotationCollectionView(
            collection_id=c.collection_id,
            name=c.name,
            annotation_types=types_by_collection_id.get(c.collection_id, []),
        )
        for c in collections
    ]


class ReadAnnotationsWithPayloadRequest(BaseModel):
    """Request body for reading annotations with payload."""

    pagination: PaginatedWithCursor
    annotation_label_ids: list[UUID] | None = None
    tag_ids: list[UUID] | None = None
    sample_ids: list[UUID] | None = None
    # Embedding-plot lasso/rectangle selection sent as geometry (a few KB) instead of the full
    # list of selected annotation sample ids; resolved to sample ids server-side (LIG-9903).
    embedding_region: EmbeddingRegion | None = None
    text_embedding: list[float] | None = None


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
            tag_ids=tag_ids,
        ),
    )


class ReadAnnotationSampleIdsRequest(BaseModel):
    """Request body for reading matching annotation sample ids."""

    filters: AnnotationsFilter | None = Field(None, description="Filter parameters for annotations")


@annotations_router.post("/annotations/sample_ids", response_model=list[UUID])
def get_annotation_sample_ids(
    collection_id: Annotated[UUID, Path(title="collection Id")],
    session: SessionDep,
    body: ReadAnnotationSampleIdsRequest,
) -> list[UUID]:
    """Retrieve all sample ids of annotations matching the given filters."""
    return list(
        annotation_resolver.get_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=body.filters,
        )
    )


@annotations_router.post("/annotations/payload")
def read_annotations_with_payload(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the collection")
    ],
    session: SessionDep,
    body: ReadAnnotationsWithPayloadRequest,
) -> AnnotationWithPayloadAndCountView:
    """Retrieve annotations with payload and optional similarity or sample filters."""
    return annotation_resolver.get_all_with_payload(
        session=session,
        pagination=Paginated(
            offset=body.pagination.offset,
            limit=body.pagination.limit,
        ),
        filters=AnnotationsFilter(
            collection_ids=[collection_id],
            annotation_label_ids=body.annotation_label_ids,
            tag_ids=body.tag_ids,
            sample_ids=body.sample_ids,
            embedding_region=body.embedding_region,
        ),
        collection_id=collection_id,
        text_embedding=body.text_embedding,
    )


@annotations_router.get(
    "/annotations/{sample_id}/embedding",
    response_model=list[float],
)
def read_annotation_embedding(
    collection_id: Annotated[
        UUID, Path(title="collection Id", description="The ID of the annotation collection")
    ],
    sample_id: Annotated[UUID, Path(title="sample Id", description="The annotation sample ID")],
    session: SessionDep,
) -> list[float]:
    """Return the stored embedding vector for a single annotation sample.

    Used for drag-to-search self-similarity: searching with an annotation's own
    stored embedding.
    """
    embedding_models = embedding_model_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
    )
    if not embedding_models:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="No embedding model is registered for this collection.",
        )

    embeddings = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=[sample_id],
        embedding_model_id=embedding_models[0].embedding_model_id,
    )
    if not embeddings:
        raise HTTPException(
            status_code=HTTP_STATUS_NOT_FOUND,
            detail="No stored embedding found for this annotation.",
        )

    return [float(value) for value in embeddings[0].embedding]


class AnnotationUpdateInput(BaseModel):
    """API input model for updating an annotation."""

    annotation_id: UUID
    collection_id: UUID
    label_name: str | None = None
    bounding_box: BoundingBoxCoordinates | None = None
    segmentation_mask: list[int] | None = None
    start_time_s: float | None = None
    end_time_s: float | None = None


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
                start_time_s=annotation_update_input.start_time_s,
                end_time_s=annotation_update_input.end_time_s,
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
) -> AnnotationView:
    """Retrieve an existing annotation from the database."""
    annotation = annotations_service.get_annotation_by_id(
        session=session, annotation_id=annotation_id
    )
    return AnnotationView.from_annotation_table(annotation=annotation)


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
