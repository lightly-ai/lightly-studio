"""Build an annotation count query on the images of a collection."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import Select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable, AnnotationType
from lightly_studio.models.annotation_label import AnnotationLabelTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def build_label_count_query(
    collection_id: UUID,
    key_columns: Sequence[Any],
    count_mode: AnnotationCountMode,
    annotation_type: AnnotationType | None = None,
    annotation_collection_ids: Sequence[UUID] | None = None,
) -> Select[Any]:
    """Count the annotations on the images of a collection, grouped by the key columns.

    Each result row holds the key columns, then the count.
    """
    # The select overloads do not cover a variable number of columns.
    query: Select[Any] = (
        select(*key_columns, annotation_count_helpers.build_count_expression(count_mode))  # type: ignore[call-overload]
        .select_from(AnnotationLabelTable)
        .join(
            AnnotationBaseTable,
            col(AnnotationBaseTable.annotation_label_id)
            == col(AnnotationLabelTable.annotation_label_id),
        )
        .join(
            ImageTable,
            col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id),
        )
        .join(
            SampleTable,
            col(SampleTable.sample_id) == col(ImageTable.sample_id),
        )
        .where(SampleTable.collection_id == collection_id)
    )
    if annotation_type is not None:
        query = query.where(col(AnnotationBaseTable.annotation_type) == annotation_type)
    if annotation_collection_ids:
        query = annotation_count_helpers.restrict_to_annotation_sources(
            query=query,
            annotation_collection_ids=list(annotation_collection_ids),
        )
    return query.group_by(*key_columns)
