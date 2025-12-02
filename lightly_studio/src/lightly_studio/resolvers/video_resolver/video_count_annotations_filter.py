"""Utility functions for building database queries."""

from typing import List, Optional

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.video import VideoFrameTable, VideoTable
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter
from lightly_studio.type_definitions import QueryType


class VideoCountAnnotationsFilter(BaseModel):
    """Encapsulates filter parameters for querying video frame annotations counter."""

    video_filter: Optional[VideoFilter] = None
    video_frames_annotations_labels: Optional[List[str]] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_annotations_label(query)

        if self.video_filter:
            query = self.video_filter.apply(query)

        return query

    def _apply_annotations_label(self, query: QueryType) -> QueryType:
        if not self.video_frames_annotations_labels:
            return query

        frame_filtered_video_ids_subquery = (
            select(VideoTable.sample_id)
            .join(VideoTable.frames)
            .join(
                AnnotationBaseTable,
                col(AnnotationBaseTable.parent_sample_id) == VideoFrameTable.sample_id,
            )
            .join(AnnotationBaseTable.annotation_label)
            .where(
                col(AnnotationLabelTable.annotation_label_name).in_(
                    self.video_frames_annotations_labels or []
                )
            )
            .distinct()
        )

        return query.where(col(VideoTable.sample_id).in_(frame_filtered_video_ids_subquery))
