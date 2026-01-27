"""Shared annotation filter helpers."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import or_
from sqlmodel import col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.type_definitions import QueryType


class AnnotationFilter(BaseModel):
    """Encapsulates annotation-based filter parameters.

    Filtering rules:
    - annotation_label_ids=None: no label filtering (include_unannotated_samples only affects counts).
    - annotation_label_ids=[]: treated as None unless preserve_empty_label_ids=True.
    - include_unannotated_samples=True with label IDs: include samples that have any of the labels
      or have no annotations at all.
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
