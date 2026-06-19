"""The grid filter: a discriminated union over the per-grid sample filters.

Per-grid sample filters are expected to implement GridFilterBase.
"""

from __future__ import annotations

from typing import Annotated, Union

from pydantic import Field

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

# TODO(Michal, 06/2026): Add GroupFilter.
GridFilter = Annotated[
    Union[ImageFilter, VideoFilter, VideoFrameFilter, AnnotationsFilter],
    Field(discriminator="filter_type"),
]
