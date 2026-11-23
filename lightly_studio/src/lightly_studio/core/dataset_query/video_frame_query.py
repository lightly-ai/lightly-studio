"""Queries for videos with matching frames."""

from sqlalchemy import ColumnElement
from sqlmodel import col, select

from lightly_studio.core.dataset_query.boolean_expression import AND, NOT, OR
from lightly_studio.core.dataset_query.classification_query import ClassificationQuery
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.object_detection_query import ObjectDetectionQuery
from lightly_studio.core.dataset_query.polygon_query import PolygonQuery
from lightly_studio.core.dataset_query.sample_evaluation_query import SampleEvaluationQuery
from lightly_studio.core.dataset_query.segmentation_mask_query import SegmentationMaskQuery
from lightly_studio.core.dataset_query.video_event_query import VideoEventQuery
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoFrameTable


class VideoFrameQuery(MatchExpression):
    """Match a video with at least one frame that satisfies all criteria.

    Separate VideoFrameQuery expressions can match different frames. Negating a
    criterion matches a frame that lacks it; negating this query matches videos
    with no matching frame, including videos without frames.
    """

    def __init__(self, *criteria: MatchExpression) -> None:
        """Combine frame criteria with AND.

        Args:
            criteria: Annotation queries, frame fields, and boolean expressions.

        Raises:
            ValueError: A criterion contains a nested frame or event query.
        """
        self._criterion = AND(*criteria)
        _validate_frame_criterion(criterion=self._criterion)

    def get(self) -> ColumnElement[bool]:
        """Get a single frame-existence expression for the combined criteria."""
        return (
            select(VideoFrameTable.sample_id)
            .where(
                col(VideoFrameTable.parent_sample_id) == col(SampleTable.sample_id),
                VideoFrameTable.sample.has(self._criterion.get()),
            )
            .correlate(SampleTable)
            .exists()
        )


def _validate_frame_criterion(criterion: MatchExpression) -> None:
    if isinstance(criterion, (VideoFrameQuery, VideoEventQuery)):
        raise ValueError("Frame criteria cannot contain frame or event queries.")
    if isinstance(criterion, (AND, OR)):
        for term in criterion.terms:
            _validate_frame_criterion(criterion=term)
    elif isinstance(criterion, NOT):
        _validate_frame_criterion(criterion=criterion.term)
    elif isinstance(
        criterion,
        (ClassificationQuery, ObjectDetectionQuery, SegmentationMaskQuery, PolygonQuery),
    ):
        _validate_frame_criterion(criterion=criterion.criterion)
    elif isinstance(criterion, SampleEvaluationQuery):
        for term in criterion.criteria:
            _validate_frame_criterion(criterion=term)
