"""Query for croppable annotations of an annotation collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from lightly_studio.models.annotation.annotation_base import (
    CROPPABLE_ANNOTATION_TYPES,
    AnnotationBaseTable,
)
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable


def build(annotation_collection_id: UUID) -> SelectOfScalar[UUID]:
    """Build the query for croppable annotations of the collection.

    Object-detection and segmentation-mask annotations are both included; each annotation
    source is assumed to hold a single annotation type.

    Results are ordered by source image path so an image's annotations stay adjacent and tend to
    land in the same chunk, preserving the single-open-per-image behaviour of crop embedding.

    Args:
        annotation_collection_id: The annotation collection to scan.

    Returns:
        A query for the annotation sample IDs, joined to their image and ordered by image path.
    """
    return (
        select(col(AnnotationBaseTable.sample_id))
        .join(SampleTable, col(SampleTable.sample_id) == col(AnnotationBaseTable.sample_id))
        .join(ImageTable, col(ImageTable.sample_id) == col(AnnotationBaseTable.parent_sample_id))
        .where(col(SampleTable.collection_id) == annotation_collection_id)
        .where(col(AnnotationBaseTable.annotation_type).in_(CROPPABLE_ANNOTATION_TYPES))
        .order_by(col(ImageTable.file_path_abs))
    )
