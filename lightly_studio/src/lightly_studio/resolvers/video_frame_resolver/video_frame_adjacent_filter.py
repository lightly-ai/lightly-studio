"""Filters for adjacent video frame queries."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from lightly_studio.resolvers.filter_with_collection_id import FilterWithCollectionId
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


class VideoFrameAdjacentFilter(BaseModel):
    """Aggregate filters for adjacent video frame lookups.

    Attributes:
        video_frame_filter: Frame-level filters (required collection_id).
        video_filter: Parent-video filters (required collection_id).
        video_text_embedding: Text embedding to order parent videos; needs video collection_id.
    """

    filter_type: Literal["video_frame_adjacent"] = "video_frame_adjacent"
    video_frame_filter: FilterWithCollectionId[VideoFrameFilter]
    video_filter: FilterWithCollectionId[VideoFilter] | None = None
    video_text_embedding: list[float] | None = None
