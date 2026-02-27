"""Filters for adjacent video frame queries."""

from __future__ import annotations

from pydantic import BaseModel

from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


class VideoFrameAdjacentFilter(BaseModel):
    """Aggregate filters for adjacent video frame lookups."""

    video_frame_filter: VideoFrameFilter
    video_filter: VideoFilter | None = None
    video_text_embedding: list[float] | None = None
