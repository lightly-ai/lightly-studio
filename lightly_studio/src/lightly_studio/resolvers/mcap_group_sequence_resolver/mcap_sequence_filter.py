"""Filter for querying MCAP sequences."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.type_definitions import QueryType


class McapSequenceFilter(GridFilterBase):
    """Encapsulates filter parameters for querying MCAP sequences.

    The query the filter is applied to must be joined to ``SampleTable`` on the
    sequence sample ID.
    """

    filter_type: Literal["mcap_sequence"] = "mcap_sequence"
    sample_filter: SampleFilter | None = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_filter:
            query = self.sample_filter.apply(query)
        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(McapGroupSequenceTable.sample_id).join(
            SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id)
        )
