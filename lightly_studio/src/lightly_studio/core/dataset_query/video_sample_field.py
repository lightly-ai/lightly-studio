"""Fields for querying video sample properties in the dataset query system."""

from __future__ import annotations

from sqlmodel import col

from lightly_studio.core.dataset_query.field import (
    ComparableField,
    NumericalField,
)
from lightly_studio.core.dataset_query.tags_expression import TagsAccessor
from lightly_studio.models.video import VideoTable


class VideoSampleField:
    """Providing access to predefined sample fields for queries.

    It is used for the `query.match(...)` and `query.order_by(...)` methods of the
    `DatasetQuery` class.

    ```python
    from lightly_studio.core.dataset_query import VideoSampleField, OrderByField

    query = dataset.query()
    query.match(VideoSampleField.tags.contains("cat"))
    query.order_by(OrderByField(VideoSampleField.file_path_abs))
    samples = query.to_list()
    ```
    """

    file_name = ComparableField(col(VideoTable.file_name))
    width = NumericalField(col(VideoTable.width))
    height = NumericalField(col(VideoTable.height))
    file_path_abs = ComparableField(col(VideoTable.file_path_abs))

    # TODO(lukas 1/2026): make duration_s more similar to NumericalField, so that we can also use
    # `<` at least on durations that are not None.
    duration_s = ComparableField(col(VideoTable.duration_s))
    fps = NumericalField(col(VideoTable.fps))

    tags = TagsAccessor()
