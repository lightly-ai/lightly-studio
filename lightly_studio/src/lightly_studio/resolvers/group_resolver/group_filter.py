"""Utility functions for building database queries for groups."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.sample import SampleTable, SampleTagLinkTable
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


# TODO(Michal, 06/2026): Inherit from GridFilterBase.
class GroupFilter(BaseModel):
    """Encapsulates filter parameters for querying groups."""

    filter_type: Literal["group"] = "group"
    sample_filter: SampleFilter | None = None

    excluded_tag_ids: list[UUID] | None = None
    """Exclude groups with any of these tags, including when inclusion filters match."""

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_filter is not None:
            query = self.sample_filter.apply(query)

        if self.excluded_tag_ids:
            tagged_samples = select(SampleTagLinkTable.sample_id).where(
                col(SampleTagLinkTable.tag_id).in_(self.excluded_tag_ids)
            )
            query = query.where(col(SampleTable.sample_id).not_in(tagged_samples))
        return query
