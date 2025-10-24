"""Utility functions for building database queries."""

from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.metadata_resolver.metadata_filter import (
    MetadataFilter,
    apply_metadata_filters,
)
from lightly_studio.type_definitions import QueryType


class FilterDimensions(BaseModel):
    """Encapsulates dimension-based filter parameters for querying samples."""

    min: Optional[int] = None
    max: Optional[int] = None


class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    width: Optional[FilterDimensions] = None
    height: Optional[FilterDimensions] = None
    annotation_label_ids: Optional[List[UUID]] = None
    tag_ids: Optional[List[UUID]] = None
    metadata_filters: Optional[List[MetadataFilter]] = None
    sample_ids: Optional[List[UUID]] = None

    def apply(self, query: QueryType) -> QueryType:
        """Apply the filters to the given query."""
        if self.sample_ids:
            query = query.where(col(ImageTable.sample_id).in_(self.sample_ids))

        # Apply dimension-based filters to the query.
        query = self._apply_dimension_filters(query)

        # Apply annotation label filters to the query.
        if self.annotation_label_ids:
            sample_ids_subquery = (
                select(AnnotationBaseTable.sample_id)
                .select_from(AnnotationBaseTable)
                .join(AnnotationBaseTable.annotation_label)
                .where(col(AnnotationLabelTable.annotation_label_id).in_(self.annotation_label_ids))
                .distinct()
            )
            query = query.where(col(ImageTable.sample_id).in_(sample_ids_subquery))

        # Apply tag filters to the query.
        if self.tag_ids:
            sample_ids_subquery = (
                select(ImageTable.sample_id)
                .select_from(ImageTable)
                .join(ImageTable.sample)
                .join(SampleTable.tags)
                .where(col(TagTable.tag_id).in_(self.tag_ids))
                .distinct()
            )
            query = query.where(col(ImageTable.sample_id).in_(sample_ids_subquery))

        # Apply metadata filters to the query.
        if self.metadata_filters:
            query = apply_metadata_filters(
                query,
                self.metadata_filters,
                metadata_model=SampleMetadataTable,
                metadata_join_condition=SampleMetadataTable.sample_id == ImageTable.sample_id,
            )
        return query

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
