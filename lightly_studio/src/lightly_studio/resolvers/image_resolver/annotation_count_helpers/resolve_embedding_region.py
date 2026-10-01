"""Resolve an embedding region to sample IDs before filtering."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.image_filter import ImageFilter


def resolve_embedding_region(
    session: Session,
    collection_id: UUID,
    image_filter: ImageFilter | None,
) -> None:
    """Resolve an embedding region to sample IDs before applying the image filter."""
    sample_filter = image_filter.sample_filter if image_filter is not None else None
    if sample_filter is None or sample_filter.embedding_region is None:
        return
    sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )
