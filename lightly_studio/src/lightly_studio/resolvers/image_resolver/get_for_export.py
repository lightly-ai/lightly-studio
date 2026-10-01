"""Implementation of get_for_export function for images."""

from __future__ import annotations

from collections.abc import Generator
from enum import Enum
from uuid import UUID

from sqlalchemy.orm import contains_eager, joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, select

from lightly_studio.core.image.image_sample import ImageSample
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


class ImageExportPreload(Enum):
    """Relationships to eagerly load when exporting images.

    Pass a frozenset of these values to ``get_for_export`` to avoid N+1 queries
    when accessing the corresponding properties on the returned ``ImageSample``s.
    """

    ANNOTATIONS = "annotations"
    CAPTIONS = "captions"


def get_for_export(
    session: Session,
    collection_id: UUID,
    collection_filter: ImageFilter | None,
    preload: frozenset[ImageExportPreload] = frozenset(),
) -> Generator[ImageSample, None, None]:
    """Return all images in a collection as a lazy generator of ImageSamples.

    If ``collection_filter`` is provided, only images matching the filter are
    returned. Embedding-region filters are resolved to concrete sample IDs
    before the query is executed.

    Args:
        session: Database session.
        collection_id: ID of the collection to export.
        collection_filter: Optional filter to restrict which images are returned.
        preload: Set of relationships to eagerly load. By default nothing is
            preloaded. Pass ``frozenset({ImageExportPreload.ANNOTATIONS})`` or
            ``frozenset({ImageExportPreload.CAPTIONS})``.

    Returns:
        Generator of ImageSamples for the matching images.
    """
    sample_options: list[LoaderOption] = []
    if ImageExportPreload.ANNOTATIONS in preload:
        sample_options.append(
            selectinload(SampleTable.annotations).options(
                joinedload(AnnotationBaseTable.annotation_label),
                joinedload(AnnotationBaseTable.object_detection_details),
                joinedload(AnnotationBaseTable.segmentation_details),
            )
        )
    if ImageExportPreload.CAPTIONS in preload:
        sample_options.append(selectinload(SampleTable.captions))

    eager_sample = contains_eager(ImageTable.sample)
    if sample_options:
        eager_sample = eager_sample.options(*sample_options)  # type: ignore[arg-type]

    query = (
        select(ImageTable)
        .join(ImageTable.sample)
        .options(eager_sample)
        .where(SampleTable.collection_id == collection_id)
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
