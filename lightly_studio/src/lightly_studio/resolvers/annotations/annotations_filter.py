"""Filtering functionality for annotations."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import Field, PrivateAttr
from sqlalchemy import false
from sqlalchemy.orm import Mapped, aliased
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.embedding_region import EmbeddingRegion
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.tag import TagTable
from lightly_studio.resolvers.grid_filter_base import GridFilterBase
from lightly_studio.type_definitions import QueryType


class AnnotationsFilter(GridFilterBase):
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
    # Lasso/rectangle selection from the embedding plot, sent as geometry (a few KB) instead
    # of the full list of selected annotation sample ids (see LIG-9903). It is resolved to
    # concrete sample ids server-side via point-in-polygon over the cached 2D projection; the
    # resolver must call `set_resolved_region_sample_ids` before this filter is applied.
    embedding_region: EmbeddingRegion | None = None

    # Sample ids the `embedding_region` resolves to, populated server-side. `None` means the
    # region has not been resolved yet; an empty list means the region encloses no points.
    _resolved_region_sample_ids: list[UUID] | None = PrivateAttr(default=None)

    def set_resolved_region_sample_ids(self, sample_ids: list[UUID]) -> None:
        """Store the annotation sample ids that ``embedding_region`` resolves to.

        Called by the region resolver before the filter is applied, since the point-in-polygon
        test needs a database session that ``apply`` does not have access to.
        """
        self._resolved_region_sample_ids = sample_ids

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

    def _has_predicates(self) -> bool:
        """Whether any filtering predicate is set."""
        return bool(
            self.collection_ids
            or self.annotation_label_ids
            or self.tag_ids
            or self.annotation_types
            or self.sample_ids
            or self.embedding_region is not None
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

        # Filter by annotation sample ids (e.g. manual selection)
        if self.sample_ids:
            query = query.where(
                db_array.in_array(
                    column=col(annotation_sample.sample_id),
                    values=self.sample_ids,
                )
            )

        # Filter by embedding-plot region selection, resolved server-side to sample ids.
        if self.embedding_region is not None:
            if self._resolved_region_sample_ids is None:
                raise RuntimeError(
                    "embedding_region must be resolved with set_resolved_region_sample_ids() "
                    "before the filter is applied."
                )
            if not self._resolved_region_sample_ids:
                # An empty region encloses no points and must match nothing (not everything).
                query = query.where(false())
            else:
                query = query.where(
                    db_array.in_array(
                        column=col(annotation_sample.sample_id),
                        values=self._resolved_region_sample_ids,
                    )
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
