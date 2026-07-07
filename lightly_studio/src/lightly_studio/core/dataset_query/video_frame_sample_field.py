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


# TODO(Malte, 07/2026): Generalize into a reusable foreign-tags accessor (mirroring
# ForeignComparableField / ForeignNumericalField) instead of a video-frame-specific class.
@dataclass
class _ParentVideoTagsContainsExpression(MatchExpression):
    """Expression checking whether a frame's parent video has a given tag."""

    tag_name: str

    def get(self) -> ColumnElement[bool]:
        """Match frames whose parent video has the given tag."""
        video_has_tag = VideoTable.sample.has(
            SampleTable.tags.any(col(TagTable.name) == self.tag_name)
        )
        return VideoFrameTable.video.has(video_has_tag)


class _ParentVideoTagsAccessor:
    """Provides tag membership queries on a frame's parent video."""

    def contains(self, tag_name: str) -> _ParentVideoTagsContainsExpression:
        """Check whether the parent video has the given tag."""
        return _ParentVideoTagsContainsExpression(tag_name=tag_name)


class _ParentVideoField:
    """Parent-video fields for filtering frames by video-level attributes and tags.

    Each field filters frames through the `VideoFrameTable.video` relationship, so it
    adds no join to the frame query.
    """

    file_path_abs = ForeignComparableField(
        column=col(VideoTable.file_path_abs), relationship=VideoFrameTable.video
    )
    file_name = ForeignComparableField(
        column=col(VideoTable.file_name), relationship=VideoFrameTable.video
    )
    width = ForeignNumericalField(column=col(VideoTable.width), relationship=VideoFrameTable.video)
    height = ForeignNumericalField(
        column=col(VideoTable.height), relationship=VideoFrameTable.video
    )
    fps = ForeignNumericalField(column=col(VideoTable.fps), relationship=VideoFrameTable.video)
    duration_s = ForeignComparableField(
        column=col(VideoTable.duration_s), relationship=VideoFrameTable.video
    )

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
