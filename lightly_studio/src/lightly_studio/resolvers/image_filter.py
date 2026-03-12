"""Utility functions for building database queries."""
# TODO(Michal, 11/2025): Move to image_resolver once CollectionTable.get_samples() is removed.

from typing import Optional

from pydantic import BaseModel

from lightly_studio.models.image import ImageTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class FilterDimensions(BaseModel):
    """Encapsulates dimension-based filter parameters for querying samples."""

    min: Optional[int] = None
    max: Optional[int] = None


class ImageFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    sample_filter: Optional[SampleFilter] = None
    width: Optional[FilterDimensions] = None
    height: Optional[FilterDimensions] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        # Apply sample filters to the query.
        if self.sample_filter is not None:
            query = self.sample_filter.apply(query)

        # Apply dimension-based filters to the query.
        query = self._apply_dimension_filters(query)

        # Return the modified query.
        return query  # noqa: RET504

    def _apply_dimension_filters(self, query: QueryType) -> QueryType:
        if self.width:
            if self.width.min is not None:
                query = query.where(ImageTable.width >= self.width.min)
            if self.width.max is not None:
                query = query.where(ImageTable.width <= self.width.max)
        if self.height:
            if self.height.min is not None:
                query = query.where(ImageTable.height >= self.height.min)
            if self.height.max is not None:
                query = query.where(ImageTable.height <= self.height.max)
        return query
