"""Resolvers for video database operations."""

from lightly_studio.resolvers.video_resolver.create import create, create_many
from lightly_studio.resolvers.video_resolver.get_all_by_dataset_id import get_all_by_dataset_id

__all__ = [
    "create",
    "create_many",
    "get_all_by_dataset_id",
]
