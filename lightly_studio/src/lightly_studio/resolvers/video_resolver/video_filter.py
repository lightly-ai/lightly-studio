"""Utility functions for building database queries."""

from typing import List, Optional
from uuid import UUID

from lightly_studio.resolvers.image_filter import FilterDimensions
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class VideoFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    width: Optional[FilterDimensions] = None
    height: Optional[FilterDimensions] = None
    annotation_label_ids: Optional[List[UUID]] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        # Apply sample filters to the query.
       
        # Apply dimension-based filters to the query.
        query = self._apply_dimension_filters(query)
        
        if self.annotation_label_ids:
            query = self._apply_annotations_ids(query)

        # Return the modified query.
        return query  # noqa: RET504

    def _apply_dimension_filters(self, query: QueryType) -> QueryType:
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
    
    def _apply_annotations_ids(self, query: QueryType) -> QueryType:
        frame_filtered_video_ids_subquery = (
            select(VideoTable.sample_id)
            .join(VideoTable.frames)
                .join(
                 AnnotationBaseTable,
                AnnotationBaseTable.parent_sample_id == VideoFrameTable.sample_id
            )
            .where(col(AnnotationBaseTable.annotation_label_id).in_(self.annotation_label_ids))
                .distinct()
            )

        return query.where(
            col(VideoTable.sample_id).in_(frame_filtered_video_ids_subquery)
        )
