"""Count the images of a collection that have no annotations."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, func, select

from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def count_images_without_annotations(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
) -> tuple[int, int]:
    """Count the images without annotations, with and without the filter.

    When the filter selects annotation sources (`annotations_filter.collection_ids`), an
    image counts if it has no annotation in those sources. The annotation classes of the
    filter are ignored: they never remove an image without annotations from the grid,
    because the "no annotations" filter combines with them by OR.

    Returns:
        A (current_count, total_count) tuple. The current count applies the other
        filters, the total count does not.
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    unannotated_filter = AnnotationsFilter(
        collection_ids=annotation_count_helpers.get_annotation_collection_ids(
            image_filter=image_filter
        ),
        include_unannotated_samples=True,
    )
    total_filter = ImageFilter(sample_filter=SampleFilter(annotations_filter=unannotated_filter))
    current_filter = _replace_annotations_filter(
        image_filter=image_filter or ImageFilter(),
        annotations_filter=unannotated_filter,
    )
    return (
        _count(session=session, collection_id=collection_id, image_filter=current_filter),
        _count(session=session, collection_id=collection_id, image_filter=total_filter),
    )


def _replace_annotations_filter(
    image_filter: ImageFilter, annotations_filter: AnnotationsFilter
) -> ImageFilter:
    sample_filter = image_filter.sample_filter or SampleFilter()
    return image_filter.model_copy(
        update={
            "sample_filter": sample_filter.model_copy(
                update={"annotations_filter": annotations_filter}
            )
        }
    )


def _count(session: Session, collection_id: UUID, image_filter: ImageFilter) -> int:
    sample_ids = image_filter.build_sample_ids_query(collection_id=collection_id).subquery()
    return session.exec(select(func.count()).select_from(sample_ids)).one()
