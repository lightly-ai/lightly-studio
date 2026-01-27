"""SampleFilter class."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.metadata import SampleMetadataTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.metadata_resolver import metadata_filter
from lightly_studio.resolvers.metadata_resolver.metadata_filter import MetadataFilter
from lightly_studio.type_definitions import QueryType


class AnnotationFilter(BaseModel):
    """Encapsulates annotation-based filter parameters.

    Similar to SampleFilter but here we focus on the annotation classes.
    We use a custom class to handle the different queries with and without
    annotations properly.
    """

    annotation_label_ids: list[UUID] | None = None
    include_unannotated_samples: bool | None = None

    @classmethod
    def from_params(
        cls,
        annotation_label_ids: list[UUID] | None,
        include_unannotated_samples: bool | None,
        preserve_empty_label_ids: bool = False,
    ) -> AnnotationFilter | None:
        """Build an AnnotationFilter from raw filter values."""
        if (
            annotation_label_ids is not None
            and not annotation_label_ids
            and not preserve_empty_label_ids
        ):
            annotation_label_ids = None
        if annotation_label_ids is None and include_unannotated_samples is None:
            return None
        return cls(
            annotation_label_ids=annotation_label_ids,
            include_unannotated_samples=include_unannotated_samples,
        )

    def allows_unannotated(self) -> bool:
        """Return True if unannotated samples should be included."""
        if self.include_unannotated_samples:
            return True
        return self.annotation_label_ids is None

    def apply_to_samples(self, query: QueryType, sample_id_column: Any) -> QueryType:
        """Apply annotation filters using the provided sample ID column."""
        if self.annotation_label_ids is None:
            return query

        annotations_sample_ids_subquery = (
            select(AnnotationBaseTable.parent_sample_id).select_from(AnnotationBaseTable).distinct()
        )

        if self.annotation_label_ids is not None:
            annotation_label_subquery = (
                select(AnnotationBaseTable.parent_sample_id)
                .select_from(AnnotationBaseTable)
                .where(col(AnnotationBaseTable.annotation_label_id).in_(self.annotation_label_ids))
                .distinct()
            )
            if self.include_unannotated_samples:
                return query.where(
                    or_(
                        sample_id_column.in_(annotation_label_subquery),
                        ~sample_id_column.in_(annotations_sample_ids_subquery),
                    )
                )
            return query.where(sample_id_column.in_(annotation_label_subquery))

        return query.where(~sample_id_column.in_(annotations_sample_ids_subquery))



class SampleFilter(BaseModel):
    """Encapsulates filter parameters for querying samples."""

    collection_id: UUID | None = None
    annotation_label_ids: list[UUID] | None = None
    include_unannotated_samples: bool | None = None
    tag_ids: list[UUID] | None = None
    metadata_filters: list[MetadataFilter] | None = None
    sample_ids: list[UUID] | None = None
    has_captions: bool | None = None

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
        annotation_filter = AnnotationFilter.from_params(
            annotation_label_ids=self.annotation_label_ids,
            include_unannotated_samples=self.include_unannotated_samples,
        )
        if not annotation_filter:
            return query

        return annotation_filter.apply_to_samples(
            query=query, sample_id_column=col(SampleTable.sample_id)
        )

    def without_annotation_filters(self) -> SampleFilter:
        """Return a copy without annotation-specific filters."""
        return self.model_copy(
            update={
                "annotation_label_ids": None,
                "include_unannotated_samples": None,
            }
        )

    def _apply_tag_filters(self, query: QueryType) -> QueryType:
        if self.tag_ids:
            sample_ids_subquery = (
                select(SampleTable.sample_id)
                .join(SampleTable.tags)
                .where(col(TagTable.tag_id).in_(self.tag_ids))
                .distinct()
            )
            return query.where(col(SampleTable.sample_id).in_(sample_ids_subquery))
        return query

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
