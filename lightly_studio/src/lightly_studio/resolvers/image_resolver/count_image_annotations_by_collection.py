"""Count annotation label totals and filtered counts for an image collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import AnnotationCountMode


def count_image_annotations_by_collection(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[tuple[str, int, int]]:
    """Count annotations for a specific image collection.

    Annotations are grouped by annotation label name and counted for total and
    filtered. Returns a list of (label_name, current_count, total_count) tuples.

    When ``annotation_type`` is provided, both the total and filtered counts are
    restricted to annotations of that type (e.g. only CLASSIFICATION or only
    OBJECT_DETECTION).

    When ``count_mode`` is ``OBJECTS`` (default), each annotation row is counted
    individually. When ``count_mode`` is ``SAMPLES``, the count reflects the number
    of distinct parent samples that carry at least one matching annotation, so a
    sample with multiple annotations of the same label is counted only once.

    When a subset of annotation source collections is selected (via the filter's
    ``annotations_filter.collection_ids``), both the total and filtered counts are
    restricted to those sources. Annotations from unselected sources are excluded
    from the total as well, so the total never counts labels the current view does
    not care about (e.g. viewing a single source shows "2 of 2", not "2 of 4").
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    annotation_collection_ids = annotation_count_helpers.get_annotation_collection_ids(
        image_filter=image_filter,
    )
    total_counts = annotation_count_helpers.get_total_counts(
        session=session,
        collection_id=collection_id,
        annotation_type=annotation_type,
        count_mode=count_mode,
        annotation_collection_ids=annotation_collection_ids,
    )
    current_counts = annotation_count_helpers.get_current_counts(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    return [
        (label, current_counts.get(label, 0), total_count)
        for label, total_count in total_counts.items()
    ]
