"""Fields for querying video frame sample properties in the dataset query system."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.dataset_query.field import NumericalField
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.video import VideoFrameTable


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
    """

    frame_number = NumericalField(col(VideoFrameTable.frame_number))
    frame_timestamp_s = NumericalField(col(VideoFrameTable.frame_timestamp_s))
    frame_timestamp_pts = NumericalField(col(VideoFrameTable.frame_timestamp_pts))
    rotation_deg = NumericalField(col(VideoFrameTable.rotation_deg))

    tags = TagsAccessor()
