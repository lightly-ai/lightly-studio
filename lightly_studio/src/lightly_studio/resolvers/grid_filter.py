"""The grid filter: a discriminated union over the four per-grid filters.

Each grid (images, videos, video frames, annotations) has its own filter type.
``GridFilter`` unifies them into a single ``filter_type``-discriminated union so a
caller can accept any grid's filter and resolve it to the sample ids it matches
without hand-parsing the request shape. Resolution is done by the filter itself via
``GridFilterBase.build_sample_ids_query``.
"""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

GridFilter = Annotated[
    Union[ImageFilter, VideoFilter, VideoFrameFilter, AnnotationsFilter],
    Field(discriminator="filter_type"),
]
