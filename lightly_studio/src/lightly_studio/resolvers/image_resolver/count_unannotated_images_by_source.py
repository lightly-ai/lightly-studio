"""Count images without annotations per annotation source."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlmodel import Session, col, exists, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.image_resolver import annotation_count_helpers
from lightly_studio.resolvers.image_resolver.annotation_count_types import UnannotatedImageCount


def count_unannotated_images_by_source(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None = None,
) -> list[UnannotatedImageCount]:
    """Count images without any annotation in each annotation source.

    An image is unannotated for a source when no annotation of that source has
    the image as its parent sample. The total count ignores the filter and the
    current count applies it.

    Args:
        session: The database session.
        collection_id: The image collection to count images in.
        image_filter: Filter that restricts the images for the current count.

    Returns:
        One entry per annotation source of the collection, also when its counts
        are zero.
    """
    annotation_count_helpers.resolve_embedding_region(
        session=session,
        collection_id=collection_id,
        image_filter=image_filter,
    )
    sources = collection_resolver.get_annotation_collections(
        session=session, parent_collection_id=collection_id
    )
    return [
        UnannotatedImageCount(
            annotation_collection_id=source.collection_id,
            current_count=_count_unannotated(
                session=session,
                collection_id=collection_id,
                source_id=source.collection_id,
                image_filter=image_filter,
            ),
            total_count=_count_unannotated(
                session=session,
                collection_id=collection_id,
                source_id=source.collection_id,
                image_filter=None,
            ),
        )
        for source in sources
    ]


def _count_unannotated(
    session: Session,
    collection_id: UUID,
    source_id: UUID,
    image_filter: ImageFilter | None,
) -> int:
    annotation_sample = aliased(SampleTable)
    has_annotation = exists(
        select(AnnotationBaseTable.sample_id)
        .join(annotation_sample, AnnotationBaseTable.sample)
        .where(
            AnnotationBaseTable.parent_sample_id == ImageTable.sample_id,
            col(annotation_sample.collection_id) == source_id,
        )
    )
    query = (
        select(func.count(col(ImageTable.sample_id)))
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(SampleTable.collection_id == collection_id, ~has_annotation)
    )
    if image_filter is not None:
        query = image_filter.apply(query)
    return session.exec(query).one()
