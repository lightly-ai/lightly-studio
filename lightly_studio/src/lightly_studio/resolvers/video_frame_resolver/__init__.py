"""Resolvers for video_frame database operations."""

from lightly_studio.resolvers.video_frame_resolver.create_many import create_many
from lightly_studio.resolvers.video_frame_resolver.get_all_by_dataset_id import (
    get_all_by_dataset_id,
)
from lightly_studio.resolvers.video_frame_resolver.get_by_id import (
    get_by_id,
)

__all__ = [
    "create_many",
    "get_all_by_dataset_id",
    "get_by_id",
]
