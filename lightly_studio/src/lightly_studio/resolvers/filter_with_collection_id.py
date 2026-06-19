"""Filter type that carries a collection ID alongside a video filter."""

from __future__ import annotations

from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.type_definitions import QueryType

# FilterWithCollectionId is used for SampleAdjacent functionality for videos.
T = TypeVar("T", VideoFrameFilter, VideoFilter)


class FilterWithCollectionId(BaseModel, Generic[T]):
    """Pairs a collection ID with a video or video frame filter."""

    collection_id: UUID
    filter: T

    def apply(
        self,
        query: QueryType,
    ) -> QueryType:
        """Apply collection scope then the inner filter to the query.

        Args:
            query: The query to filter.
        """
        scoped = query.where(col(SampleTable.collection_id) == self.collection_id)
        return self.filter.apply(scoped)
