"""Filter type that carries a collection ID alongside a video filter."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col

from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.type_definitions import QueryType


class FilterWithCollectionId(BaseModel):
    """Pairs a collection ID with a video or video frame filter."""

    collection_id: UUID
    filter: VideoFrameFilter | VideoFilter

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
