"""Filter for querying MCAP sequences."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
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
    group_annotation_filter: AnnotationsFilter | None = None
    """Keeps the sequences with a group that has a matching annotation."""

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_filter:
            query = self.sample_filter.apply(query)
        if self.group_annotation_filter:
            query = self._apply_group_annotation_filter(
                query=query, group_annotation_filter=self.group_annotation_filter
            )
        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(McapGroupSequenceTable.sample_id).join(
            SampleTable, col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id)
        )

    @staticmethod
    def _apply_group_annotation_filter(
        query: QueryType, group_annotation_filter: AnnotationsFilter
    ) -> QueryType:
        sequence_ids = group_annotation_filter.apply_to_parent_sample_query(
            query=select(SampleSequenceLinkTable.sequence_sample_id),
            sample_id_column=col(SampleSequenceLinkTable.sample_id),
        )
        return query.where(col(McapGroupSequenceTable.sample_id).in_(sequence_ids))
