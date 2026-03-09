"""Filtering functionality for annotations."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy.orm import aliased
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.type_definitions import QueryType


class AnnotationsFilter(BaseModel):
    """Handles filtering for annotation queries."""

    annotation_types: list[AnnotationType] | None = Field(
        default=None,
        description="Types of annotation to filter (e.g., 'object_detection')",
    )
    collection_ids: list[UUID] | None = Field(default=None, description="List of collection UUIDs")
    annotation_label_ids: list[UUID] | None = Field(
        default=None, description="List of annotation label UUIDs"
    )
    tag_ids: list[UUID] | None = Field(default=None, description="List of tag UUIDs")

    sample_ids: list[UUID] | None = Field(
        default=None, description="List of sample UUIDs to filter annotations by"
    )

    def apply(
        self,
        query: QueryType,
    ) -> QueryType:
        """Apply filters to an annotation query.

        Args:
            query: The base query to apply filters to
            annotation_table: The SQLModel table class for the annotation type

        Returns:
            The query with filters applied
        """
        annotation_sample = aliased(SampleTable)
        query = query.join(annotation_sample, AnnotationBaseTable.sample)
        return self._apply_annotation_filters(
            query=query,
            annotation_sample=annotation_sample,
        )

    def apply_to_sample_query(
        self,
        query: QueryType,
        sample_id_column: Any,
    ) -> QueryType:
        """Filter a parent-sample query by annotation criteria.

        This is used when the base query returns samples, but the filter itself
        is defined on annotations. The sample query is constrained to the parent
        sample ids produced by `get_parent_sample_ids_subquery()`.
        """
        sample_ids_subquery = self.get_parent_sample_ids_subquery()
        return query.where(sample_id_column.in_(sample_ids_subquery))

    def get_parent_sample_ids_subquery(self) -> Any:
        """Build a subquery selecting parent sample ids for matching annotations.

        The subquery reuses the same annotation predicates as `apply()`, but
        returns `AnnotationBaseTable.parent_sample_id` instead of annotation
        rows.
        """
        annotation_sample = aliased(SampleTable)
        query = select(AnnotationBaseTable.parent_sample_id).join(
            annotation_sample,
            AnnotationBaseTable.sample,
        )
        query = self._apply_annotation_filters(
            query=query,
            annotation_sample=annotation_sample,
        )
        return query.distinct()

    def _apply_annotation_filters(
        self,
        query: QueryType,
        annotation_sample: Any,
    ) -> QueryType:
        """Apply the shared annotation predicates to a joined query.

        Both `apply()` and `get_parent_sample_ids_subquery()` call this helper
        so the annotation filtering rules live in one place.
        """
        # Filter by collection
        if self.collection_ids:
            query = query.where(col(annotation_sample.collection_id).in_(self.collection_ids))

        # Filter by annotation label
        if self.annotation_label_ids:
            query = query.where(
                col(AnnotationBaseTable.annotation_label_id).in_(self.annotation_label_ids)
            )

        # Filter by tags
        if self.tag_ids:
            query = (
                query.join(annotation_sample.tags)
                .where(annotation_sample.tags.any(col(TagTable.tag_id).in_(self.tag_ids)))
                .distinct()
            )

        # Filter by sample ids
        if self.sample_ids:
            query = query.where(col(AnnotationBaseTable.parent_sample_id).in_(self.sample_ids))

        # Filter by annotation type
        if self.annotation_types:
            query = query.where(col(AnnotationBaseTable.annotation_type).in_(self.annotation_types))

        return query
