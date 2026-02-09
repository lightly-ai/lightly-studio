"""Utility functions for building database queries for groups."""

from typing import Optional

from pydantic import BaseModel

from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class GroupFilter(BaseModel):
    """Encapsulates filter parameters for querying groups."""

    sample_filter: Optional[SampleFilter] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_filter is not None:
            query = self.sample_filter.apply(query)

        return query
