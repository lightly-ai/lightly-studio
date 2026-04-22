"""SampleFilter class."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.core.dataset_query import query_translation
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.query_expr import QueryExpr
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.type_definitions import QueryType


class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    tag_ids: Optional[list[UUID]] = None
    metadata_filters: Optional[list[MetadataFilter]] = None
    sample_ids: Optional[list[UUID]] = None
    has_captions: Optional[bool] = None
    annotations_filter: Optional[AnnotationsFilter] = None
    query_expr: Optional[QueryExpr] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_sample_ids_filter(query)
        query = self._apply_annotation_filters(query)
        query = self._apply_tag_filters(query)
        query = self._apply_metadata_filters(query)
        query = self._apply_captions_filter(query)
        return self._apply_query_expr_filter(query)

    def _apply_sample_ids_filter(self, query: QueryType) -> QueryType:
        if self.sample_ids:
            return query.where(col(SampleTable.sample_id).in_(self.sample_ids))
        return query

    def _apply_annotation_filters(self, query: QueryType) -> QueryType:
        if self.annotations_filter is None:
            return query
        return self.annotations_filter.apply_to_parent_sample_query(
            query=query,
            sample_id_column=col(SampleTable.sample_id),
        )

    def _apply_tag_filters(self, query: QueryType) -> QueryType:
        if not self.tag_ids:
            return query

        sample_ids_subquery = (
            select(SampleTable.sample_id)
            .join(SampleTable.tags)
            .where(col(TagTable.tag_id).in_(self.tag_ids))
            .distinct()
        )
        return query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))

    def _apply_metadata_filters(self, query: QueryType) -> QueryType:
        if self.metadata_filters:
            return metadata_filter.apply_metadata_filters(
                query,
                self.metadata_filters,
                metadata_model=SampleMetadataTable,
                metadata_join_condition=SampleMetadataTable.sample_id == SampleTable.sample_id,
            )
        return query

    def _apply_captions_filter(self, query: QueryType) -> QueryType:
        if self.has_captions is None:
            return query
        if self.has_captions:
            return query.where(col(SampleTable.captions).any())
        return query.where(~col(SampleTable.captions).any())

    def _apply_query_expr_filter(self, query: QueryType) -> QueryType:
        if self.query_expr is None:
            return query
        match_expression = query_translation.to_match_expression(self.query_expr.match_expr)
        return query.where(match_expression.get())
