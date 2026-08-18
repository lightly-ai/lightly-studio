"""API route for annotation counts grouped by sample tags."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.collection import CollectionTable
from lightly_studio.resolvers import image_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
    SampleTagAnnotationCounts,
)

count_by_sample_tags_router = APIRouter()


class ReadCountImageAnnotationsBySampleTagsRequest(BaseModel):
    """Request body for annotation counts grouped by sample tag."""

    sample_tag_ids: list[UUID] = Field(
        description=(
            "Ordered sample tag IDs to count independently. The response preserves this order; "
            "an empty list returns no series."
        ),
    )
    filter: ImageFilter | None = Field(
        None,
        description=(
            "Active image filter applied in addition to each selected sample tag. This can "
            "include a separate active sample-tag filter."
        ),
    )
    annotation_type: AnnotationType | None = Field(
        None,
        description="Restrict counts to a single annotation type (e.g. classification).",
    )
    count_mode: AnnotationCountMode = Field(
        AnnotationCountMode.OBJECTS,
        description="Whether to count annotation objects or distinct annotated samples.",
    )


class AnnotationClassCountView(BaseModel):
    """Annotation count for one class."""

    label_name: str = Field(description="Annotation class name on the shared class axis.")
    count: int = Field(
        description="Number of matching annotation objects or distinct annotated samples."
    )


class SampleTagAnnotationCountsView(BaseModel):
    """Annotation class counts for one sample tag."""

    sample_tag_id: UUID = Field(description="ID of the selected sample tag.")
    sample_tag_name: str = Field(description="Name of the selected sample tag.")
    counts: list[AnnotationClassCountView] = Field(
        description=(
            "Counts on the shared, alphabetically ordered class axis. Missing classes have a "
            "count of zero."
        )
    )


@count_by_sample_tags_router.post(
    "/annotations/count-by-sample-tags",
    response_model=list[SampleTagAnnotationCountsView],
)
def count_image_annotations_by_sample_tags(
    collection: Annotated[
        CollectionTable,
        Path(title="collection Id"),
        Depends(get_and_validate_collection_id),
    ],
    session: SessionDep,
    body: ReadCountImageAnnotationsBySampleTagsRequest,
) -> list[SampleTagAnnotationCounts]:
    """Get image annotation counts grouped by selected sample tags.

    Args:
        collection: Target image collection resolved from the path parameter.
        session: Database session for the request.
        body: Selected sample tags, active image filter, annotation scope, and count mode.

    Returns:
        One zero-filled class-count series per requested sample tag, in request order.
    """
    return image_resolver.count_image_annotations_by_sample_tags(
        session=session,
        collection_id=collection.collection_id,
        sample_tag_ids=body.sample_tag_ids,
        image_filter=body.filter,
        annotation_type=body.annotation_type,
        count_mode=body.count_mode,
    )
