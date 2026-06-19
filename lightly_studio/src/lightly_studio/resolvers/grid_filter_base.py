"""Shared base class for the per-grid filters.

Each grid (images, videos, video frames, annotations) has its own filter type.
They all resolve to the same shape of "distinct sample ids in a collection that
match this filter", differing only in which base query they start from. This base
captures that shared algorithm and leaves the one varying step -- the base select
-- abstract for each concrete filter to supply.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.sample import SampleTable
from lightly_studio.type_definitions import QueryType


class GridFilterBase(BaseModel, ABC):
    """Base class for filters that resolve to the sample ids they match."""

    @abstractmethod
    def apply(self, query: QueryType) -> QueryType:
        """Apply this filter's predicates to the given query."""

    def build_sample_ids_query(self, collection_id: UUID) -> SelectOfScalar[UUID]:
        """Build the query selecting distinct sample ids matching this filter.

        Args:
            collection_id: The ID of the collection to scope results to.

        Returns:
            A query selecting the distinct sample ids the filter matches.
        """
        query = self._select_sample_ids()
        query = query.where(col(SampleTable.collection_id) == collection_id)
        query = self.apply(query)
        return query.distinct()

    @abstractmethod
    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        """Return the base query selecting ``sample_id``, joined to ``SampleTable``."""
