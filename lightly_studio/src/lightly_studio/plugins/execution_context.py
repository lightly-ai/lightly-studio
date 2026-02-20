"""Execution context passed to operators at runtime."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


@dataclass
class ExecutionContext:
    """Contextual data passed to ``BaseOperator.execute()``.

    ``filter=None`` means the whole collection, while a non-null filter
    restricts the target samples.
    """

    collection_id: UUID
    filter: ImageFilter | VideoFilter | None = None
