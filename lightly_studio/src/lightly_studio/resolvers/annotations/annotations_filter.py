"""Filtering functionality for annotations."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlalchemy.orm import Mapped, aliased
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.type_definitions import QueryType


class CollectionLabelFilter(BaseModel):
    """Filter for annotations within a specific annotation collection."""

    collection_id: UUID
    annotation_label_ids: list[UUID] | None = Field(
        default=None,
        description="Label IDs to include; None means all labels in the collection",
    )


class AnnotationsFilter(BaseModel):
    """Handles filtering for annotation queries."""

    filter_type: Literal["annotations"] = "annotations"
    annotation_types: list[AnnotationType] | None = Field(
        default=None,
        description="Types of annotation to filter (e.g., 'object_detection')",
    )
    collection_ids: list[UUID] | None = Field(default=None, description="List of collection UUIDs")
    annotation_label_ids: list[UUID] | None = Field(
        default=None, description="List of annotation label UUIDs"
    )
    tag_ids: list[UUID] | None = Field(default=None, description="List of tag UUIDs")
    per_collection_label_filters: list[CollectionLabelFilter] | None = Field(
        default=None,
        description=(
            "Per-collection label filters expressed as disjunctive conditions: "
            "an annotation matches if it belongs to any listed collection with its label "
            "in the corresponding allowed set. When set, overrides collection_ids and "
            "annotation_label_ids."
        ),
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

    def apply_to_parent_sample_query(
        self,
        query: QueryType,
        sample_id_column: Mapped[UUID],
    ) -> QueryType:
        """Filter a parent-sample query by annotation criteria.

        This is used when the base query returns samples, but the filter itself
        is defined on annotations. The sample query is constrained to the parent
        sample ids of annotations matching this filter.
        """
        annotation_sample = aliased(SampleTable)
        sample_ids_subquery = select(AnnotationBaseTable.parent_sample_id).join(
            annotation_sample,
            AnnotationBaseTable.sample,
        )
        sample_ids_subquery = self._apply_annotation_filters(
            query=sample_ids_subquery,
            annotation_sample=annotation_sample,
        )
        return query.where(sample_id_column.in_(sample_ids_subquery.distinct()))

    def _apply_annotation_filters(
        self,
        query: QueryType,
        annotation_sample: type[SampleTable],
    ) -> QueryType:
        """Apply the shared annotation predicates to a joined query.

        Both `apply()` and `apply_to_parent_sample_query()` call this helper so
        the annotation filtering rules live in one place.
        """
        # Per-collection label filter: (collection=A AND label IN [...]) OR (collection=B AND ...)
        if self.per_collection_label_filters:
            conditions = []
            for cf in self.per_collection_label_filters:
                cond = col(annotation_sample.collection_id) == cf.collection_id
                if cf.annotation_label_ids is not None:
                    cond = and_(
                        cond,
                        col(AnnotationBaseTable.annotation_label_id).in_(cf.annotation_label_ids),
                    )
                conditions.append(cond)
            query = query.where(or_(*conditions))
        else:
            # Fall back to flat filters when per_collection_label_filters is not set
            if self.collection_ids:
                query = query.where(col(annotation_sample.collection_id).in_(self.collection_ids))

            if self.annotation_label_ids:
                query = query.where(
                    col(AnnotationBaseTable.annotation_label_id).in_(self.annotation_label_ids)
                )

        # Filter by tags
        if self.tag_ids:
            query = query.where(annotation_sample.tags.any(col(TagTable.tag_id).in_(self.tag_ids)))

        # Filter by annotation type
        if self.annotation_types:
            query = query.where(col(AnnotationBaseTable.annotation_type).in_(self.annotation_types))

        return query
