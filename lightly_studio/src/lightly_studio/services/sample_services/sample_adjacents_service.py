"""Get samples adjacent to a given sample."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session

from lightly_studio.models.adjacents import AdjacentResultView
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    annotation_resolver,
    image_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import (
    AnnotationsFilter,
)
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import (
    VideoFrameFilter,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


class AdjacentRequest(BaseModel):
    """Request body for reading adjacent samples."""

    sample_type: SampleType
    filters: ImageFilter | VideoFilter | VideoFrameFilter | AnnotationsFilter
    text_embedding: list[float] | None = None


def get_adjacent_samples(
    session: Session, sample_id: UUID, request: AdjacentRequest
) -> AdjacentResultView | None:
    """Get adjacent samples.

    Args:
        session: Database session for executing the operation.
        sample_id: The ID of the sample for which to retrieve adjacent samples.
        request: The request parameters for filtering adjacent samples.

    Returns:
        The adjacent samples result with previous/next IDs and position.
    """
    if request.sample_type == SampleType.IMAGE:
        if not isinstance(request.filters, ImageFilter):
            raise ValueError(
                "Invalid filter provided. Expected ImageFilter"
                f" for sample type '{request.sample_type.value}'."
            )
        return image_resolver.get_adjacent_images(
            session=session,
            filters=request.filters,
            text_embedding=request.text_embedding,
            sample_id=sample_id,
        )
    if request.sample_type == SampleType.VIDEO:
        if not isinstance(request.filters, VideoFilter):
            raise ValueError(
                "Invalid filter provided. Expected VideoFilter"
                f" for sample type '{request.sample_type.value}'."
            )
        return video_resolver.get_adjacent_videos(
            session=session,
            filters=request.filters,
            text_embedding=request.text_embedding,
            sample_id=sample_id,
        )
    if request.sample_type == SampleType.VIDEO_FRAME:
        if not isinstance(request.filters, VideoFrameFilter):
            raise ValueError(
                "Invalid filter provided. Expected VideoFrameFilter"
                f" for sample type '{request.sample_type.value}'."
            )
        return video_frame_resolver.get_adjacent_video_frames(
            session=session,
            filters=request.filters,
            sample_id=sample_id,
        )
    if request.sample_type == SampleType.ANNOTATION:
        if not isinstance(request.filters, AnnotationsFilter):
            raise ValueError(
                "Invalid filter provided. Expected AnnotationsFilter"
                f" for sample type '{request.sample_type.value}'."
            )
        return annotation_resolver.get_adjacent_annotations(
            session=session,
            filters=request.filters,
            sample_id=sample_id,
        )
    raise NotImplementedError(
        f"Adjacent samples retrieval is not implemented for sample type: {request.sample_type}"
    )
