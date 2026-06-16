"""This module contains the API routes for sampling."""

from __future__ import annotations

from typing import Annotated, Union

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.db_manager import SessionDep
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import image_resolver, video_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.sampling.sampling_config import (
    AnnotationClassBalancingStrategy,
    EmbeddingDeduplicationStrategy,
    EmbeddingDiversityStrategy,
    EmbeddingSimilarityStrategy,
    MetadataWeightingStrategy,
    SamplingConfig,
)
from lightly_studio.sampling.sampling_via_db import sampling_via_database

sampling_router = APIRouter()

Strategy = Annotated[
    Union[
        AnnotationClassBalancingStrategy,
        EmbeddingDeduplicationStrategy,
        EmbeddingDiversityStrategy,
        EmbeddingSimilarityStrategy,
        MetadataWeightingStrategy,
    ],
    Field(discriminator="strategy_name"),
]

CollectionFilter = Annotated[
    Union[ImageFilter, VideoFilter],
    Field(discriminator="filter_type"),
]


class SamplingRequest(BaseModel):
    """Request model for sampling."""

    n_samples_to_select: int = Field(gt=0, description="Number of samples to select")
    sampling_result_tag_name: str = Field(min_length=1, description="Name for the result tag")
    strategies: list[Strategy]
    filter: CollectionFilter | None = None


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
    if collection.sample_type not in (SampleType.IMAGE, SampleType.VIDEO):
        raise HTTPException(
            status_code=400,
            detail="Sampling is only supported for image and video collections.",
        )
    # Get all samples in collection as input for sampling.
    if collection.sample_type == SampleType.IMAGE:
        if request.filter is None:
            image_filter = None
        elif isinstance(request.filter, ImageFilter):
            image_filter = request.filter
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid filter type for image collection.",
            )
        all_samples_result = image_resolver.get_sample_ids(
            session=session,
            collection_id=collection.collection_id,
            filters=image_filter,
        )
    else:
        if request.filter is None:
            video_filter = None
        elif isinstance(request.filter, VideoFilter):
            video_filter = request.filter
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid filter type for video collection.",
            )
        all_samples_result = video_resolver.get_sample_ids(
            session=session,
            collection_id=collection.collection_id,
            filters=video_filter,
        )
    input_sample_ids = list(all_samples_result)
    # Validate we have enough samples to select from.
    if len(input_sample_ids) < request.n_samples_to_select:
        raise HTTPException(
            status_code=400,
            detail=f"collection has only {len(input_sample_ids)} samples, "
            f"cannot select {request.n_samples_to_select}",
        )
    # Create SamplingConfig with diversity strategy.
    config = SamplingConfig(
        collection_id=collection.collection_id,
        n_samples_to_select=request.n_samples_to_select,
        sampling_result_tag_name=request.sampling_result_tag_name,
        strategies=request.strategies,
    )
    # Perform sampling via database.
    sampling_via_database(session=session, config=config, input_sample_ids=input_sample_ids)
