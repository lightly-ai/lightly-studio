"""Resolvers for evaluation results."""

from lightly_studio.resolvers.evaluation_result_resolver.create import create
from lightly_studio.resolvers.evaluation_result_resolver.get_all import get_all, get_by_id

__all__ = ["create", "get_all", "get_by_id"]
