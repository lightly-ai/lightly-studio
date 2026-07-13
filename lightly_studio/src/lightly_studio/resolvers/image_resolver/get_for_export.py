"""Implementation of get_for_export function for images."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def get_for_export(
    session: Session,
    collection_id: UUID,
    collection_filter: ImageFilter | None,
) -> Generator[ImageSample, None, None]:
    """Return all images in a collection as a lazy generator of ImageSamples.

    If ``collection_filter`` is provided, only images matching the filter are
    returned. Embedding-region filters are resolved to concrete sample IDs
    before the query is executed.

    Args:
        session: Database session.
        collection_id: ID of the collection to export.
        collection_filter: Optional filter to restrict which images are returned.

    Returns:
        Generator of ImageSamples for the matching images.
    """
    query = (
        select(ImageTable).join(ImageTable.sample).where(SampleTable.collection_id == collection_id)
    )
    if collection_filter is not None:
        sample_filter = collection_filter.sample_filter
        if sample_filter is not None and sample_filter.embedding_region is not None:
            region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
                session=session,
                collection_id=collection_id,
                region=sample_filter.embedding_region,
            )
            resolved_sample_filter = sample_filter.model_copy(
                update={"region_sample_ids": region_sample_ids}
            )
            collection_filter = collection_filter.model_copy(
                update={"sample_filter": resolved_sample_filter}
            )
        query = query.where(
            col(SampleTable.sample_id).in_(collection_filter.build_sample_ids_query(collection_id))
        )
    return (ImageSample(row) for row in session.exec(query))
