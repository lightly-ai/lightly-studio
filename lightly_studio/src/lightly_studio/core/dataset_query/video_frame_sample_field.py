"""Fields for querying video frame sample properties in the dataset query system."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import ColumnElement
from sqlmodel import col

from lightly_studio.core.dataset_query.field import NumericalField
from lightly_studio.core.dataset_query.foreign_field import (
    ForeignComparableField,
    ForeignNumericalField,
)
from lightly_studio.core.dataset_query.match_expression import MatchExpression
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.models.video import VideoFrameTable, VideoTable


@dataclass
class _ParentVideoTagsContainsExpression(MatchExpression):
    """Expression checking whether a frame's parent video has a given tag."""

    tag_name: str

    def get(self) -> ColumnElement[bool]:
        """Return a correlated EXISTS over the parent video's tags."""
        return VideoFrameTable.video.has(
            VideoTable.sample.has(SampleTable.tags.any(col(TagTable.name) == self.tag_name))
        )


class _ParentVideoTagsAccessor:
    """Provides tag membership queries on a frame's parent video."""

    def contains(self, tag_name: str) -> _ParentVideoTagsContainsExpression:
        """Check whether the parent video has the given tag."""
        return _ParentVideoTagsContainsExpression(tag_name=tag_name)


class _ParentVideoField:
    """Parent-video fields for filtering frames by video-level attributes and tags.

    Each field builds a correlated `EXISTS` over the `VideoFrameTable.video`
    relationship, so filtering by these does not require joining the video table.
    """

    file_path_abs = ForeignComparableField(col(VideoTable.file_path_abs), VideoFrameTable.video)
    file_name = ForeignComparableField(col(VideoTable.file_name), VideoFrameTable.video)
    width = ForeignNumericalField(col(VideoTable.width), VideoFrameTable.video)
    height = ForeignNumericalField(col(VideoTable.height), VideoFrameTable.video)
    fps = ForeignNumericalField(col(VideoTable.fps), VideoFrameTable.video)
    duration_s = ForeignComparableField(col(VideoTable.duration_s), VideoFrameTable.video)

    tags = _ParentVideoTagsAccessor()


class VideoFrameSampleField:
    """Providing access to predefined video frame fields for queries.

    It is used for the `query.match(...)` and `query.order_by(...)` methods of the
    `DatasetQuery` class.

    ```python
    from lightly_studio.core.dataset_query import VideoFrameSampleField, OrderByField

    frames = video_dataset.frames()
    query = frames.match(VideoFrameSampleField.frame_number > 10)
    query = query.order_by(OrderByField(VideoFrameSampleField.frame_timestamp_s))
    ```

    Parent-video attributes and tags are available through `parent_video`:
    ```python
    frames.match(VideoFrameSampleField.parent_video.file_path_abs == "/data/a.mp4")
    frames.match(VideoFrameSampleField.parent_video.width > 1920)
    frames.match(VideoFrameSampleField.parent_video.tags.contains("reviewed"))
    ```
    """

    frame_number = NumericalField(col(VideoFrameTable.frame_number))
    frame_timestamp_s = NumericalField(col(VideoFrameTable.frame_timestamp_s))
    frame_timestamp_pts = NumericalField(col(VideoFrameTable.frame_timestamp_pts))
    rotation_deg = NumericalField(col(VideoFrameTable.rotation_deg))

    tags = TagsAccessor()
    parent_video = _ParentVideoField()
