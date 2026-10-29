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
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
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
    has_embedding: bool | None = Field(
        default=None,
        description="Keep only annotations with (True) or without (False) an embedding",
    )
    include_unannotated_samples: bool = Field(
        default=False,
        description=(
            "Also match parent samples without annotations. When collection_ids is set, only "
            "annotations in those collections count. Only used for parent-sample queries."
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

        With `include_unannotated_samples`, samples without annotations in the
        selected collections also match. Combined with other predicates, a sample
        matches if it has a matching annotation or has no annotation at all.
        """
        matching = sample_id_column.in_(
            self._select_parent_sample_ids(apply_predicates=True).distinct()
        )
        if not self.include_unannotated_samples:
            return query.where(matching)

        # Samples with no annotation in the selected collections. Only the collection
        # scope applies here, the other predicates describe annotations that exist.
        unannotated = sample_id_column.not_in(
            self._select_parent_sample_ids(apply_predicates=False).distinct()
        )
        if not self._has_match_predicates():
            return query.where(unannotated)
        return query.where(or_(matching, unannotated))

    def _select_parent_sample_ids(self, apply_predicates: bool) -> SelectOfScalar[UUID]:
        """Select parent sample ids of annotations in the selected collections.

        Args:
            apply_predicates: Also apply the label, tag, type and sample predicates.
        """
        annotation_sample = aliased(SampleTable)
        query = select(AnnotationBaseTable.parent_sample_id).join(
            annotation_sample,
            AnnotationBaseTable.sample,
        )
        if apply_predicates:
            return self._apply_annotation_filters(query=query, annotation_sample=annotation_sample)
        if self.collection_ids:
            query = query.where(
                db_array.in_array(
                    column=col(annotation_sample.collection_id),
                    values=self.collection_ids,
                )
            )
        return query

    def _has_predicates(self) -> bool:
        """Whether any filtering predicate is set."""
        return bool(self.collection_ids or self._has_match_predicates())

    def _has_match_predicates(self) -> bool:
        """Whether a predicate other than the collection scope is set."""
        return bool(
            self.annotation_label_ids
            or self.tag_ids
            or self.annotation_types
            or self.sample_ids
            or self.region_sample_ids is not None
            or self.has_embedding is not None
        )

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

        # Filter by whether an embedding of any model exists
        if self.has_embedding is not None:
            embedded_sample_ids = select(SampleEmbeddingTable.sample_id)
            sample_id = col(annotation_sample.sample_id)
            query = query.where(
                sample_id.in_(embedded_sample_ids)
                if self.has_embedding
                else sample_id.notin_(embedded_sample_ids)
            )

        return query

    def _select_sample_ids(self) -> SelectOfScalar[UUID]:
        return select(AnnotationBaseTable.sample_id).join(AnnotationBaseTable.sample)
