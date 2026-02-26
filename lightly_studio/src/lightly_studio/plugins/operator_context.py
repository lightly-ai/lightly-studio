"""Scope definitions for operator execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from lightly_studio.models.collection import SampleType
<<<<<<< jonas-lig-8791-supported_scopes-abstract-property-on-baseoperator
from lightly_studio.resolvers.image_filter import ImageFilter
=======
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
>>>>>>> main
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


@dataclass
class ExecutionContext:
    """Contextual data passed to ``BaseOperator.execute()``.

    ``filter=None`` means the whole collection, while a non-null filter
    restricts the target samples.
    """

    collection_id: UUID
<<<<<<< jonas-lig-8791-supported_scopes-abstract-property-on-baseoperator
    filter: ImageFilter | VideoFilter | None = None
=======
    filter: (
        ImageFilter | VideoFrameFilter | VideoFilter | AnnotationsFilter | GroupFilter | None
    ) = None
>>>>>>> main


class OperatorScope(str, Enum):
    """Scope in which an operator can be triggered.

    Operators declare which scopes they support via ``BaseOperator.supported_scopes``.
    The UI uses this to surface operators contextually by media type.
    """

    ROOT = "root"
    """Operate on the root collection (dataset-level)."""

    IMAGE = "image"
<<<<<<< jonas-lig-8791-supported_scopes-abstract-property-on-baseoperator
    """Operate on images and video frames."""

    VIDEO_FRAME = "video_frame"
    """Operate on images and video frames."""

    VIDEO = "video"
    """Operate on the currently selected video."""
=======
    """Operate on images."""

    VIDEO_FRAME = "video_frame"
    """Operate on video frames."""

    VIDEO = "video"
    """Operate on videos."""
>>>>>>> main

    ANNOTATION = "annotation"
    """Operate on annotations."""

    GROUP = "group"
    """Operate on groups."""

    CAPTION = "caption"
    """Operate on captions."""


def get_allowed_scopes_for_collection(
<<<<<<< jonas-lig-8791-supported_scopes-abstract-property-on-baseoperator
    *, sample_type: SampleType, is_root_collection: bool
=======
    sample_type: SampleType, is_root_collection: bool
>>>>>>> main
) -> list[OperatorScope]:
    """Return the scopes that are valid for a collection context."""
    scope = OperatorScope(sample_type.value)
    if is_root_collection:
        return [OperatorScope.ROOT, scope]
    return [scope]
