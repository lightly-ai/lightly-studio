"""Count the images without annotations for an image collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.unannotated_sample_count import UnannotatedSampleCount
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter


def count_unannotated_images(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
) -> UnannotatedSampleCount:
    """Count the images without annotations in the selected annotation sources.

    The annotation sources come from `image_filter.sample_filter.annotations_filter`.
    Without sources, an image is unannotated if it has no annotation at all.
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session, collection_id=collection_id, image_filter=image_filter
    )
    annotations_filter = AnnotationsFilter(
        collection_ids=annotation_count_helpers.get_annotation_collection_ids(
            image_filter=image_filter
        ),
        include_unannotated_samples=True,
    )
    return sample_resolver.count_unannotated_samples(
        session=session,
        collection_id=collection_id,
        grid_filter=annotation_count_helpers.strip_source_only_annotations_filter(
            image_filter=image_filter
        )
        or ImageFilter(),
        unannotated_filter=ImageFilter(
            sample_filter=SampleFilter(annotations_filter=annotations_filter)
        ),
    )
