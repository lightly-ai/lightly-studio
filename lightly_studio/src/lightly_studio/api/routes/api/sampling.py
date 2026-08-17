"""This module contains the API routes for sampling."""

from __future__ import annotations

from typing import Annotated, Union
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from lightly_studio.api.routes.api.collection import get_and_validate_collection_id
from lightly_studio.database.db_manager import SessionDep
from lightly_studio.errors import InvalidSamplingRequestError, InvalidTagError
from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.resolvers import image_resolver, tag_resolver, video_resolver
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
    preselected_tag_id: UUID | None = Field(
        default=None,
        description=(
            "Sample tag whose samples should be considered already selected and included in the "
            "result tag"
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
    preselected_sample_ids = _get_preselected_sample_ids(
        session=session,
        collection_id=collection.collection_id,
        preselected_tag_id=request.preselected_tag_id,
    )
    input_sample_ids.extend(set(preselected_sample_ids) - set(input_sample_ids))
    _validate_sample_count(
        input_sample_ids=input_sample_ids,
        preselected_sample_ids=preselected_sample_ids,
        n_samples_to_select=request.n_samples_to_select,
    )
    # Create SamplingConfig with diversity strategy.
    config = SamplingConfig(
        collection_id=collection.collection_id,
        n_samples_to_select=request.n_samples_to_select,
        sampling_result_tag_name=request.sampling_result_tag_name,
        strategies=request.strategies,
    )
    # Perform sampling via database.
    sampling_via_database(
        session=session,
        config=config,
        input_sample_ids=input_sample_ids,
        preselected_sample_ids=preselected_sample_ids,
    )


def _get_preselected_sample_ids(
    session: Session,
    collection_id: UUID,
    preselected_tag_id: UUID | None,
) -> list[UUID]:
    """Resolve and validate the optional preselected sample tag."""
    if preselected_tag_id is None:
        return []
    tag = tag_resolver.get_by_id(session=session, tag_id=preselected_tag_id)
    if tag is None or tag.collection_id != collection_id or tag.kind != "sample":
        raise InvalidTagError("Invalid preselected sample tag.")
    return tag_resolver.get_sample_ids_by_tag_id(session=session, tag_id=preselected_tag_id)


def _validate_sample_count(
    input_sample_ids: list[UUID],
    preselected_sample_ids: list[UUID],
    n_samples_to_select: int,
) -> None:
    """Validate the requested sample count against the available candidates."""
    n_candidates = len(input_sample_ids) - len(preselected_sample_ids)
    if n_candidates < n_samples_to_select:
        candidates_description = (
            "samples not in the preselected set" if preselected_sample_ids else "samples"
        )
        raise InvalidSamplingRequestError(
            f"collection has only {n_candidates} {candidates_description}, "
            f"cannot select {n_samples_to_select}",
        )
