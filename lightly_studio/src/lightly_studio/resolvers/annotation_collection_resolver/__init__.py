"""Resolvers for annotation collections."""

from lightly_studio.resolvers.annotation_collection_resolver.create import create
from lightly_studio.resolvers.annotation_collection_resolver.get_all import get_all
from lightly_studio.resolvers.annotation_collection_resolver.get_by_name import get_by_name
from lightly_studio.resolvers.annotation_collection_resolver.resolve_collections import (
    resolve_collections,
)

__all__ = ["create", "get_all", "get_by_name", "resolve_collections"]
