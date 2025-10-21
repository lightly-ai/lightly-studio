"""Filtering functionality for annotations."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field
from sqlmodel import col

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
    dataset_ids: list[UUID] | None = Field(default=None, description="List of dataset UUIDs")
    annotation_label_ids: list[UUID] | None = Field(
        default=None, description="List of annotation label UUIDs"
    )
    annotation_tag_ids: list[UUID] | None = Field(default=None, description="List of tag UUIDs")
    sample_tag_ids: list[UUID] | None = Field(
        default=None,
        description="List of sample tag UUIDs to filter annotations by",
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
        # Filter by dataset
        if self.dataset_ids:
            query = query.where(col(AnnotationBaseTable.dataset_id).in_(self.dataset_ids))

        # Filter by annotation label
        if self.annotation_label_ids:
            query = query.where(
                col(AnnotationBaseTable.annotation_label_id).in_(self.annotation_label_ids)
            )

        # Filter by annotation tags
        if self.annotation_tag_ids:
            query = (
                query.join(AnnotationBaseTable.tags)
                .where(
                    AnnotationBaseTable.tags.any(col(TagTable.tag_id).in_(self.annotation_tag_ids))
                )
                .distinct()
            )

        # Filter by sample tags
        if self.sample_tag_ids:
            query = (
                query.join(AnnotationBaseTable.sample)
                .join(SampleTable.tags)
                .where(SampleTable.tags.any(col(TagTable.tag_id).in_(self.sample_tag_ids)))
                .distinct()
            )

        # Filter by annotation type
        if self.annotation_types:
            query = query.where(col(AnnotationBaseTable.annotation_type).in_(self.annotation_types))

        return query
