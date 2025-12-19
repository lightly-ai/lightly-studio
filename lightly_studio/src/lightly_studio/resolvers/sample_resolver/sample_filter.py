"""SampleFilter class."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.type_definitions import QueryType


class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    collection_id: Optional[UUID] = None
    annotation_label_ids: Optional[List[UUID]] = None
    tag_ids: Optional[List[UUID]] = None
    metadata_filters: Optional[List[MetadataFilter]] = None
    sample_ids: Optional[List[UUID]] = None
    has_captions: Optional[bool] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.collection_id:
            query = query.where(col(SampleTable.collection_id) == self.collection_id)

        if self.sample_ids:
            query = query.where(col(SampleTable.sample_id).in_(self.sample_ids))

        # Apply annotation label filters to the query.
        if self.annotation_label_ids:
            sample_ids_subquery = (
                select(AnnotationBaseTable.parent_sample_id)
                .select_from(AnnotationBaseTable)
                .join(AnnotationBaseTable.annotation_label)
                .where(col(AnnotationLabelTable.annotation_label_id).in_(self.annotation_label_ids))
                .distinct()
            )
            query = query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))

        # Apply tag filters to the query.
        if self.tag_ids:
            sample_ids_subquery = (
                select(SampleTable.sample_id)
                .join(SampleTable.tags)
                .where(col(TagTable.tag_id).in_(self.tag_ids))
                .distinct()
            )
            query = query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))

        # Apply metadata filters to the query.
        if self.metadata_filters:
            query = metadata_filter.apply_metadata_filters(
                query,
                self.metadata_filters,
                metadata_model=SampleMetadataTable,
                metadata_join_condition=SampleMetadataTable.sample_id == SampleTable.sample_id,
            )

        # Apply caption presence filter to the query.
        if self.has_captions is not None:
            if self.has_captions:
                query = query.where(col(SampleTable.captions).any())
            else:
                query = query.where(~col(SampleTable.captions).any())

        return query
