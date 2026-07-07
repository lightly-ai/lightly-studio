"""Utility functions for building database queries for groups."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


# TODO(Michal, 06/2026): Inherit from GridFilterBase.
class GroupFilter(BaseModel):
    """Encapsulates filter parameters for querying groups."""

    filter_type: Literal["group"] = "group"
    sample_filter: SampleFilter | None = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_filter is not None:
            query = self.sample_filter.apply(query)

        return query
