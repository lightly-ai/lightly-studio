"""Utility functions for building database queries."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col

from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class VideoFrameFilter(BaseModel):
    """Encapsulates filter parameters for querying video frames."""

    frame_number: Optional[FilterDimensions] = None
    video_id: Optional[UUID] = None
    sample_filter: Optional[SampleFilter] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_frame_number_filters(query)
        query = self._apply_video_id(query)

        if self.sample_filter:
            query = self.sample_filter.apply(query)

        return query

    def _apply_video_id(self, query: QueryType) -> QueryType:
        if self.video_id:
            return query.where(col(VideoTable.sample_id) == self.video_id)

        return query

    def _apply_frame_number_filters(self, query: QueryType) -> QueryType:
        min_frame_number = (
            self.frame_number.min
            if self.frame_number and self.frame_number.min is not None
            else None
        )

        max_frame_number = (
            self.frame_number.max
            if self.frame_number and self.frame_number.max is not None
            else None
        )

        if min_frame_number is not None:
            query = query.where(col(VideoFrameTable.frame_number) >= min_frame_number)

        if max_frame_number is not None:
            query = query.where(col(VideoFrameTable.frame_number) <= max_frame_number)

        return query
