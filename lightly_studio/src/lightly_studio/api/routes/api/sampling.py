"""This module contains the API routes for sampling."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import image_resolver, mcap_group_sequence_resolver, video_resolver
from lightly_studio.resolvers.grid_filter import SamplingFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.mcap_group_sequence_resolver.mcap_sequence_filter import (
    McapSequenceFilter,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.sampling.sampling_config import (
    SamplingConfig,
    Strategy,
)
from lightly_studio.sampling.sampling_via_db import sampling_via_database
from lightly_studio.services import sampling_metadata, sampling_service

sampling_router = APIRouter()


class SamplingRequest(BaseModel):
    """Request model for sampling."""

    n_samples_to_select: int = Field(gt=0, description="Number of samples to select")
    sampling_result_tag_name: str = Field(min_length=1, description="Name for the result tag")
    strategies: list[Strategy]
    metadata_computations: list[sampling_metadata.MetadataComputation] = Field(default_factory=list)
    filter: SamplingFilter | None = None
    preselected_tag_id: UUID | None = Field(
        default=None,
        description=(
            "Sample tag whose samples should be considered already selected and included in the "
            "result"
        ),
    )


@sampling_router.post(
    "/collections/{collection_id}/sampling",
    status_code=204,
    response_model=None,
)
def create_sampling(
    session: SessionDep,
    collection: Annotated[
        CollectionTable,
        Depends(get_and_validate_collection_id),
    ],
    request: SamplingRequest,
) -> None:
    """Create a combination sampling on the collection.

    This endpoint performs combination sampling using embeddings and metadata.
    The selected samples are tagged with the specified tag name.

    Args:
        session: Database session dependency.
        collection: collection to perform sampling on.
        request: Sampling parameters including sample count and tag name.

    Returns:
        None (204 No Content on success).

    Raises:
        HTTPException: 400 if sampling fails due to invalid parameters or other errors.
    """
    input_sample_ids = list(
        _get_input_sample_ids(session=session, collection=collection, filters=request.filter)
    )
    preselected_tag_name = sampling_service.validate_preselection(
        session=session,
        collection_id=collection.collection_id,
        preselected_tag_id=request.preselected_tag_id,
        input_sample_ids=input_sample_ids,
        n_samples_to_select=request.n_samples_to_select,
    )
    # Create SamplingConfig with diversity strategy.
    config = SamplingConfig(
        collection_id=collection.collection_id,
        n_samples_to_select=request.n_samples_to_select,
        sampling_result_tag_name=request.sampling_result_tag_name,
        strategies=request.strategies,
        preselected_tag_name=preselected_tag_name,
    )
    # Keep preparation and selection in one request so closing the browser cannot skip selection.
    sampling_metadata.compute_metadata(
        session=session, collection=collection, computations=request.metadata_computations
    )
    sampling_via_database(session=session, config=config, input_sample_ids=input_sample_ids)


def _get_input_sample_ids(
    session: Session, collection: CollectionTable, filters: SamplingFilter | None
) -> set[UUID]:
    """Get the sample IDs of the collection that match the filter, as input for sampling.

    Raises:
        HTTPException: 400 if the collection does not support sampling, or the filter is
            for another sample type than the collection.
    """
    sample_type = collection.sample_type
    if sample_type == SampleType.IMAGE and (filters is None or isinstance(filters, ImageFilter)):
        return image_resolver.get_sample_ids(
            session=session, collection_id=collection.collection_id, filters=filters
        )
    if sample_type == SampleType.VIDEO and (filters is None or isinstance(filters, VideoFilter)):
        return video_resolver.get_sample_ids(
            session=session, collection_id=collection.collection_id, filters=filters
        )
    if sample_type == SampleType.SEQUENCE and (
        filters is None or isinstance(filters, McapSequenceFilter)
    ):
        return mcap_group_sequence_resolver.get_sample_ids(
            session=session, collection_id=collection.collection_id, filters=filters
        )
    if sample_type not in (SampleType.IMAGE, SampleType.VIDEO, SampleType.SEQUENCE):
        raise HTTPException(
            status_code=400,
            detail="Sampling is only supported for image, video and sequence collections.",
        )
    raise HTTPException(
        status_code=400,
        detail=f"Invalid filter type for {sample_type.value} collection.",
    )
