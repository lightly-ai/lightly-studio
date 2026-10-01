"""Match annotations on a video or on any of its frames."""

from __future__ import annotations

from typing import Union

from sqlalchemy import ColumnElement, or_
from sqlalchemy.orm import aliased
from sqlmodel import col, select

from lightly_studio.core.dataset_query.classification_query import ClassificationQuery
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_query import ObjectDetectionQuery
from lightly_studio.core.dataset_query.segmentation_mask_query import SegmentationMaskQuery
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable

AnnotationQuery = Union[ClassificationQuery, ObjectDetectionQuery, SegmentationMaskQuery]


class VideoFrameAnnotationQuery(MatchExpression):
    """Query if a video, or any frame of the video, has an annotation matching a criterion.

    Video annotations are usually attached to the frames, not to the video sample. This
    expression matches the video when the video sample itself or one of its frames has a
    matching annotation.

    Example:
        ```python
        VideoFrameAnnotationQuery(
            ObjectDetectionQuery(ObjectDetectionField.class_name == "car")
        )
        ```
    """

    annotation_query: AnnotationQuery

    def __init__(self, annotation_query: AnnotationQuery) -> None:
        """Wrap an annotation query to also match the annotations of the video frames.

        Args:
            annotation_query: The annotation query that a video or frame annotation must match.
        """
        self.annotation_query = annotation_query

    def get(self) -> ColumnElement[bool]:
        """Get the video frame annotation match expression."""
        # Video list queries join the first frame through an unaliased VideoFrameTable.
        # The alias prevents the subquery from correlating with that join.
        frame = aliased(VideoFrameTable)
        video_ids_with_matching_frames = (
            select(frame.parent_sample_id)
            .join(
                AnnotationBaseTable,
                col(AnnotationBaseTable.parent_sample_id) == frame.sample_id,
            )
            .where(self.annotation_query.get_annotation_criterion())
        )
        return or_(
            self.annotation_query.get(),
            col(SampleTable.sample_id).in_(video_ids_with_matching_frames),
        )
