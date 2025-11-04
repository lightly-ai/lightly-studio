"""Resolvers for video database operations."""

from lightly_studio.resolvers.video_resolver.create_many import create_many
from lightly_studio.resolvers.video_resolver.get_all_by_dataset_id import get_all_by_dataset_id

__all__ = [
    "create_many",
    "get_all_by_dataset_id",
]
