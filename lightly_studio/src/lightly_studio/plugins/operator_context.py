"""Scope definitions for operator execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


@dataclass
class ExecutionContext:
    """Contextual data passed to ``BaseOperator.execute()``.

    ``filter=None`` means the whole collection, while a non-null filter
    restricts the target samples.
    """

    collection_id: UUID
    filter: (
        ImageFilter | VideoFrameFilter | VideoFilter | AnnotationsFilter | GroupFilter | None
    ) = None


class OperatorScope(str, Enum):
    """Scope in which an operator can be triggered.

    Operators declare which scopes they support via ``BaseOperator.supported_scopes``.
    The UI uses this to surface operators contextually by media type.
    """

    ROOT = "root"
    """Operate on the root collection (dataset-level)."""

    IMAGE = "image"
    """Operate on images."""

    VIDEO_FRAME = "video_frame"
    """Operate on video frames."""

    VIDEO = "video"
    """Operate on videos."""

    ANNOTATION = "annotation"
    """Operate on annotations."""

    GROUP = "group"
    """Operate on groups."""

    CAPTION = "caption"
    """Operate on captions."""


def get_allowed_scopes_for_collection(
    sample_type: SampleType, is_root_collection: bool
) -> list[OperatorScope]:
    """Return the scopes that are valid for a collection context."""
    scope = OperatorScope(sample_type.value)
    if is_root_collection:
        return [OperatorScope.ROOT, scope]
    return [scope]
