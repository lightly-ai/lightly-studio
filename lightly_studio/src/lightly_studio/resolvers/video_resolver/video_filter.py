"""Utility functions for building database queries."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.range import FloatRange
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class VideoFilter(BaseModel):
    """Encapsulates filter parameters for querying videos."""

    width: Optional[FilterDimensions] = None
    height: Optional[FilterDimensions] = None
    fps: Optional[FloatRange] = None
    duration_s: Optional[FloatRange] = None
    annotation_frames_label_ids: Optional[List[UUID]] = None
    sample_filter: Optional[SampleFilter] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_width_and_height_filters(query)
        query = self._apply_fps_filters(query)
        query = self._apply_duration_filters(query)

        if self.annotation_frames_label_ids:
            query = self._apply_annotations_ids(query)
        if self.sample_filter:
            query = self.sample_filter.apply(query)

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

    def _apply_annotations_ids(self, query: QueryType) -> QueryType:
        frame_filtered_video_ids_subquery = (
            select(VideoTable.sample_id)
            .join(VideoTable.frames)
            .join(
                AnnotationBaseTable,
                col(AnnotationBaseTable.parent_sample_id) == VideoFrameTable.sample_id,
            )
            .where(
                col(AnnotationBaseTable.annotation_label_id).in_(
                    self.annotation_frames_label_ids or []
                )
            )
            .distinct()
        )

        return query.where(col(VideoTable.sample_id).in_(frame_filtered_video_ids_subquery))
