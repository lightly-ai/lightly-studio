"""SampleFilter class."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.type_definitions import QueryType


class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    collection_id: Optional[UUID] = None
    annotation_label_ids: Optional[list[UUID]] = None
    tag_ids: Optional[list[UUID]] = None
    metadata_filters: Optional[list[MetadataFilter]] = None
    sample_ids: Optional[list[UUID]] = None
    has_captions: Optional[bool] = None
    annotations_filter: Optional[AnnotationsFilter] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        query = self._apply_collection_filter(query)
        query = self._apply_sample_ids_filter(query)
        query = self._apply_annotation_filters(query)
        query = self._apply_tag_filters(query)
        query = self._apply_metadata_filters(query)
        return self._apply_captions_filter(query)

    def _apply_collection_filter(self, query: QueryType) -> QueryType:
        if self.collection_id:
            return query.where(col(SampleTable.collection_id) == self.collection_id)
        return query

    def _apply_sample_ids_filter(self, query: QueryType) -> QueryType:
        if self.sample_ids:
            return query.where(col(SampleTable.sample_id).in_(self.sample_ids))
        return query

    def _apply_annotation_filters(self, query: QueryType) -> QueryType:
        annotations_filter = self.annotations_filter
        # TODO(Horatiu, 03/2026): This is temporary until we refactor the resolvers to use the
        # AnnotationsFilter directly instead of passing the annotation_label_ids to SampleFilter.
        if annotations_filter is None and self.annotation_label_ids:
            annotations_filter = AnnotationsFilter(annotation_label_ids=self.annotation_label_ids)
        if annotations_filter is None:
            return query
        return annotations_filter.apply_to_parent_sample_query(
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
