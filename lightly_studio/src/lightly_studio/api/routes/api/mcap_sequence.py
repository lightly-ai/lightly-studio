"""API routes for MCAP sequences."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, Field

from lightly_studio.api.dependencies.identity import IdentityDep
from lightly_studio.api.dependencies.workflow_scope import scope_to_caller
from lightly_studio.api.routes.api.validators import Paginated, PaginatedWithCursor
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.models.mcap_group_sequence import McapSequenceViewsWithCount
from lightly_studio.resolvers import mcap_group_sequence_resolver
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.video_resolver.count_video_frame_annotations_by_collection import (
    CountAnnotationsView,
)

mcap_sequence_router = APIRouter(tags=["mcap_sequence"])


class ReadMcapSequencesRequest(BaseModel):
    """Request body for reading MCAP sequences."""

    filter: McapSequenceFilter | None = Field(
        None, description="Filter parameters for MCAP sequences"
    )
    text_embedding: list[float] | None = Field(None, description="Text embedding to search for")


class ReadMcapSequenceSampleIdsRequest(BaseModel):
    """Request body for reading matching MCAP sequence sample ids."""

    filter: McapSequenceFilter | None = Field(
        None, description="Filter parameters for MCAP sequences"
    )


class ReadMcapSequenceCountAnnotationsRequest(BaseModel):
    """Request body for counting the annotation labels of MCAP sequences."""

    filter: McapSequenceFilter | None = Field(
        None, description="Filter parameters for MCAP sequences"
    )
    annotation_type: AnnotationType | None = Field(
        None,
        description="Restrict counts to a single annotation type (e.g. classification).",
    )


@mcap_sequence_router.post(
    "/collections/{collection_id}/mcap-sequences/list",
    response_model=McapSequenceViewsWithCount,
)
def list_mcap_sequences(
    session: SessionDep,
    identity: IdentityDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    pagination: Annotated[PaginatedWithCursor, Depends()],
    body: ReadMcapSequencesRequest | None = None,
) -> McapSequenceViewsWithCount:
    """Retrieve a paginated list of MCAP sequences for a collection.

    Args:
        session: The database session.
        identity: The user; a labeler sees only their own batch files.
        collection_id: The ID of the collection to fetch sequences for.
        pagination: Pagination parameters including offset (cursor) and limit.
        body: Optional filters and text embedding to search for.

    Returns:
        A paginated list of MCAP sequences with total count and next cursor.
    """
    filters = scope_to_caller(
        identity=identity,
        filters=body.filter if body is not None else None,
        empty=McapSequenceFilter,
    )
    return mcap_group_sequence_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        pagination=Paginated(offset=pagination.offset, limit=pagination.limit),
        filters=filters,
        text_embedding=body.text_embedding if body is not None else None,
    )


@mcap_sequence_router.post(
    "/collections/{collection_id}/mcap-sequences/sample_ids",
    response_model=list[UUID],
)
def get_mcap_sequence_sample_ids(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    body: ReadMcapSequenceSampleIdsRequest,
) -> list[UUID]:
    """Retrieve all sample ids of MCAP sequences matching the given filters."""
    return list(
        mcap_group_sequence_resolver.get_sample_ids(
            session=session,
            collection_id=collection_id,
            filters=body.filter,
        )
    )


@mcap_sequence_router.post(
    "/collections/{collection_id}/mcap-sequences/annotations/count",
    response_model=list[CountAnnotationsView],
)
def count_mcap_sequence_annotations_by_collection(
    session: SessionDep,
    collection_id: Annotated[UUID, Path(title="Collection Id")],
    body: ReadMcapSequenceCountAnnotationsRequest,
) -> list[CountAnnotationsView]:
    """Count the MCAP sequences of each annotation label, in total and after the filter.

    A sequence counts for a label when one of its groups has an annotation with that label.
    """
    return mcap_group_sequence_resolver.count_annotations_by_collection(
        session=session,
        collection_id=collection_id,
        filters=body.filter,
        annotation_type=body.annotation_type,
    )
