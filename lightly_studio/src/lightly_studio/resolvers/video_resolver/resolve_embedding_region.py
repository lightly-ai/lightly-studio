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
) -> None:
    """Resolve the sample region in the video filter to sample IDs in place."""
    sample_filter = video_filter.sample_filter if video_filter is not None else None
    if sample_filter is None or sample_filter.embedding_region is None:
        return

    sample_filter.region_sample_ids = embedding_region_resolver.get_sample_ids_in_region(
        session=session,
        collection_id=collection_id,
        region=sample_filter.embedding_region,
    )
