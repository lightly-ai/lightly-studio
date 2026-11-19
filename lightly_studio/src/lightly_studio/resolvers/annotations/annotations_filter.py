"""Filtering functionality for annotations."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field
from sqlalchemy.orm import Mapped, aliased
from sqlmodel import col, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.resolvers.region_sample_ids_filter import RegionSampleIdsFilter
from lightly_studio.type_definitions import QueryType


class AnnotationsFilter(GridFilterBase, RegionSampleIdsFilter):
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
    sample_ids: list[UUID] | None = Field(
        default=None, description="List of annotation sample UUIDs to restrict to"
    )
    include_unannotated_samples: bool = Field(
        default=False,
        description=(
            "Also match parent samples without annotations in the selected annotation "
            "sources. Applies only to parent sample queries."
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
        if not self._has_predicates():
            # Skip the unused join; it would only add a redundant sample scan.
            return query
        # TODO(Michal, 06/2026): When predicates are set this aliased join scans
        # sample a second time (the base query already joined it for collection
        # scoping). Reuse the base join instead of aliasing a new one.
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

        If `include_unannotated_samples` is set, parent samples without annotations in
        the selected annotation sources also match. Without annotation predicates other
        than the sources, only these parent samples match.
        """
        is_matching = sample_id_column.in_(self.select_matching_parent_sample_ids())
        if not self.include_unannotated_samples:
            return query.where(is_matching)
        is_unannotated = sample_id_column.not_in(self.select_annotated_parent_sample_ids())
        if not self.has_annotation_predicates():
            return query.where(is_unannotated)
        return query.where(or_(is_matching, is_unannotated))

    def select_matching_parent_sample_ids(self) -> SelectOfScalar[UUID]:
        """Select the distinct parent sample ids of annotations that match this filter."""
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

    def select_annotated_parent_sample_ids(self) -> SelectOfScalar[UUID]:
        """Select the parent sample ids of annotations in the selected annotation sources."""
        query = select(AnnotationBaseTable.parent_sample_id)
        if not self.collection_ids:
            return query
        return query.join(AnnotationBaseTable.sample).where(
            db_array.in_array(column=col(SampleTable.collection_id), values=self.collection_ids)
        )

    def has_annotation_predicates(self) -> bool:
        """Whether a predicate other than the annotation sources is set."""
        return bool(
            self.annotation_label_ids
            or self.tag_ids
            or self.annotation_types
            or self.sample_ids
            or self.region_sample_ids is not None
        )

    def is_source_only(self) -> bool:
        """Whether every field except `collection_ids` has its default value."""
        # Compare all fields, so that a field added later keeps the filter.
        exclude = {"collection_ids"}
        return self.model_dump(exclude=exclude) == AnnotationsFilter().model_dump(exclude=exclude)

    def _has_predicates(self) -> bool:
        """Whether any filtering predicate is set."""
        return bool(self.collection_ids) or self.has_annotation_predicates()

    def _apply_annotation_filters(
        self,
        query: QueryType,
        annotation_sample: type[SampleTable],
    ) -> QueryType:
        """Apply the shared annotation predicates to a joined query.

        Both `apply()` and `apply_to_parent_sample_query()` call this helper so
        the annotation filtering rules live in one place.
        """
        # Filter by collection
        if self.collection_ids:
            query = query.where(
                db_array.in_array(
                    column=col(annotation_sample.collection_id),
                    values=self.collection_ids,
                )
            )

        # Filter by annotation sample ids (e.g. embedding plot selection)
        if self.sample_ids:
            query = query.where(
                db_array.in_array(
                    column=col(annotation_sample.sample_id),
                    values=self.sample_ids,
                )
            )

        # Filter by embedding-plot region selection, resolved server-side to sample ids.
        query = self._apply_region_sample_ids_filter(
            query, sample_id_column=col(annotation_sample.sample_id)
        )

        # Filter by annotation label
        if self.annotation_label_ids:
            query = query.where(
                db_array.in_array(
                    column=col(AnnotationBaseTable.annotation_label_id),
                    values=self.annotation_label_ids,
                )
            )

        # Filter by tags
        if self.tag_ids:
            query = query.where(
                annotation_sample.tags.any(
                    db_array.in_array(column=col(TagTable.tag_id), values=self.tag_ids)
                )
            )

        # Filter by annotation type
        if self.annotation_types:
            query = query.where(col(AnnotationBaseTable.annotation_type).in_(self.annotation_types))

        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(AnnotationBaseTable.sample_id).join(AnnotationBaseTable.sample)
