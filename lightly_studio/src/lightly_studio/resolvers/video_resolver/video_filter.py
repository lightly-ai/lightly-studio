"""Utility functions for building database queries."""

from typing import Optional

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.range import FloatRange
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class VideoFilter(BaseModel):
    """Encapsulates filter parameters for querying videos."""

    width: Optional[FilterDimensions] = None
    height: Optional[FilterDimensions] = None
    fps: Optional[FloatRange] = None
    duration_s: Optional[FloatRange] = None
    sample_filter: Optional[SampleFilter] = None
    frame_annotation_filter: Optional[AnnotationsFilter] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_width_and_height_filters(query)
        query = self._apply_fps_filters(query)
        query = self._apply_duration_filters(query)

        if self.sample_filter:
            query = self.sample_filter.apply(query)
        if self.frame_annotation_filter is not None:
            query = self._apply_annotation_filter(query)

        return query

    def _apply_width_and_height_filters(self, query: QueryType) -> QueryType:
        if self.width:
            if self.width.min is not None:
                query = query.where(VideoTable.width >= self.width.min)
            if self.width.max is not None:
                query = query.where(VideoTable.width <= self.width.max)
        if self.height:
            if self.height.min is not None:
                query = query.where(VideoTable.height >= self.height.min)
            if self.height.max is not None:
                query = query.where(VideoTable.height <= self.height.max)
        return query

    def _apply_fps_filters(self, query: QueryType) -> QueryType:
        min_fps = self.fps.min if self.fps and self.fps.min is not None else None
        max_fps = self.fps.max if self.fps and self.fps.max is not None else None

        if min_fps is not None:
            query = query.where(VideoTable.fps >= min_fps)

        if max_fps is not None:
            query = query.where(VideoTable.fps <= max_fps)

        return query

    def _apply_duration_filters(self, query: QueryType) -> QueryType:
        min_duration_s = (
            self.duration_s.min if self.duration_s and self.duration_s.min is not None else None
        )

        max_duration_s = (
            self.duration_s.max if self.duration_s and self.duration_s.max is not None else None
        )

        if min_duration_s is not None:
            query = query.where(col(VideoTable.duration_s) >= min_duration_s)

        if max_duration_s is not None:
            query = query.where(col(VideoTable.duration_s) <= max_duration_s)

        return query

    def _apply_annotation_filter(self, query: QueryType) -> QueryType:
        """For videos, annotation filters are applied to the frames."""
        assert self.frame_annotation_filter is not None

        frame_filtered_video_ids_subquery = select(VideoFrameTable.parent_sample_id)
        frame_filtered_video_ids_subquery = (
            self.frame_annotation_filter.apply_to_parent_sample_query(
                query=frame_filtered_video_ids_subquery,
                sample_id_column=col(VideoFrameTable.sample_id),
            )
        )

        return query.where(col(VideoTable.sample_id).in_(frame_filtered_video_ids_subquery))
