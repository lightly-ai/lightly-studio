"""The grid filter: a discriminated union over the four per-grid filters.

Each grid (images, videos, video frames, annotations) has its own filter type.
``GridFilter`` unifies them into a single ``filter_type``-discriminated union so a
caller can accept any grid's filter and resolve it to the sample ids it matches
without hand-parsing the request shape.
"""

from __future__ import annotations

from typing import Annotated, Union
from uuid import UUID

from pydantic import Field
from typing_extensions import assert_never
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.resolvers import (
    annotation_resolver,
    image_resolver,
    video_frame_resolver,
    video_resolver,
)
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

GridFilter = Annotated[
    Union[ImageFilter, VideoFilter, VideoFrameFilter, AnnotationsFilter],
    Field(discriminator="filter_type"),
]


def build_sample_ids_query(
    grid_filter: GridFilter,
    collection_id: UUID,
) -> SelectOfScalar[UUID]:
    """Dispatch a grid filter to its resolver's ``build_sample_ids_query``.

    Each branch scopes to ``collection_id`` and applies the filter, returning a
    query selecting the distinct sample ids the grid filter matches.
    """
    if isinstance(grid_filter, ImageFilter):
        return image_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    if isinstance(grid_filter, VideoFilter):
        return video_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    if isinstance(grid_filter, VideoFrameFilter):
        return video_frame_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    if isinstance(grid_filter, AnnotationsFilter):
        return annotation_resolver.build_sample_ids_query(
            collection_id=collection_id, filters=grid_filter
        )
    assert_never(grid_filter)
