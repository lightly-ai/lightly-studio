"""Resolve embedding regions in video filters."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import embedding_region_resolver
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def resolve_embedding_region(
    session: Session,
    collection_id: UUID,
    video_filter: VideoFilter | None,
) -> VideoFilter | None:
    """Return a copied video filter with its sample region resolved to sample IDs."""
    if video_filter is None:
        return None

    resolved_filter = video_filter.model_copy(deep=True)
    sample_filter = resolved_filter.sample_filter
    if sample_filter is None or sample_filter.embedding_region is None:
        return resolved_filter

    sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )
    return resolved_filter
