"""Count annotation totals and filtered counts per annotation type for an image collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def count_image_annotations_by_type(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[tuple[AnnotationType, int, int]]:
    """Count annotations of an image collection, grouped by annotation type.

    This is the annotation-type counterpart of
    :func:`count_image_annotations_by_collection`, which groups by annotation class. It backs
    the sidebar's "Annotation Types" filter group, so every type the collection contains is
    returned even when the active filter leaves none of them visible — a group that vanished
    once its count reached zero could not be unchecked again.

    Args:
        session: Database session.
        collection_id: Collection whose images are counted.
        image_filter: Active image filter; only the filtered count uses it.
        count_mode: Count annotation objects, or distinct annotated samples.

    Returns:
        A (annotation_type, current_count, total_count) tuple per type present in the
        collection, ordered by the enum's declaration order.
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    annotation_collection_ids = annotation_count_helpers.get_annotation_collection_ids(
        image_filter=image_filter,
    )
    total_counts = annotation_count_helpers.get_counts_by_type(
        session=session,
        collection_id=collection_id,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    current_counts = annotation_count_helpers.get_counts_by_type(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    return [
        (annotation_type, current_counts.get(annotation_type, 0), total_counts[annotation_type])
        for annotation_type in AnnotationType
        if annotation_type in total_counts
    ]
