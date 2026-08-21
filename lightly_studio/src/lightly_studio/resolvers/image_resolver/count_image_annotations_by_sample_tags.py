"""Count image annotation label totals per sample tag."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationType
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import (
    AnnotationCountMode,
    SampleTagAnnotationCounts,
)


def count_image_annotations_by_sample_tags(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    sample_tag_ids: Sequence[UUID],
    image_filter: ImageFilter | None = None,
    annotation_type: AnnotationType | None = None,
    count_mode: AnnotationCountMode = AnnotationCountMode.OBJECTS,
) -> list[SampleTagAnnotationCounts]:
    """Count image annotations independently for each requested sample tag.

    The active image filter is intersected with each sample tag. Annotation source
    restrictions inside the filter also scope the shared class axis.

    Args:
        session: Database session used to validate tags and execute count queries.
        collection_id: ID of the image collection whose annotations are counted.
        sample_tag_ids: Ordered sample tag IDs. Empty input returns no series.
        image_filter: Active image filter applied in addition to each sample tag.
        annotation_type: Optional annotation type restriction.
        count_mode: Whether to count annotation objects or distinct parent samples.

    Returns:
        One zero-filled class-count series per requested tag, preserving request order.

    Raises:
        ValueError: If a requested ID is not a sample tag in the target collection.
    """
    if not sample_tag_ids:
        return []

    sample_tags = annotation_count_helpers.get_and_validate_sample_tags(
        session=session,
        collection_id=collection_id,
        sample_tag_ids=sample_tag_ids,
    )
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    annotation_collection_ids = annotation_count_helpers.get_annotation_collection_ids(
        image_filter=image_filter,
    )
    class_names = list(
        annotation_count_helpers.get_total_counts(
            session=session,
            collection_id=collection_id,
            annotation_type=annotation_type,
            count_mode=count_mode,
            annotation_collection_ids=annotation_collection_ids,
        )
    )
    grouped_counts = annotation_count_helpers.get_counts_grouped_by_sample_tag(
        session=session,
        collection_id=collection_id,
        sample_tag_ids=sample_tag_ids,
        image_filter=image_filter,
        annotation_type=annotation_type,
        annotation_collection_ids=annotation_collection_ids,
        count_mode=count_mode,
    )
    return annotation_count_helpers.build_sample_tag_counts(
        sample_tag_ids=sample_tag_ids,
        sample_tags=sample_tags,
        class_names=class_names,
        grouped_counts=grouped_counts,
    )
