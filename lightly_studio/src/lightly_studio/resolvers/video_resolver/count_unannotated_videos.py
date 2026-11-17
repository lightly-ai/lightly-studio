"""Count the videos without annotations for a video collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.unannotated_sample_count import UnannotatedSampleCount
from lightly_studio.resolvers import sample_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.video_resolver.resolve_embedding_region import (
    resolve_embedding_region,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def count_unannotated_videos(
    session: Session,
    collection_id: UUID,
    video_filter: VideoFilter | None = None,
) -> UnannotatedSampleCount:
    """Count the videos without annotations on the video or on one of its frames.

    The annotation sources come from `video_filter.frame_annotation_filter`. Without
    sources, a video is unannotated if neither it nor its frames have an annotation.
    """
    resolve_embedding_region(
        session=session, collection_id=collection_id, video_filter=video_filter
    )
    frame_annotation_filter = video_filter.frame_annotation_filter if video_filter else None
    annotations_filter = AnnotationsFilter(
        collection_ids=frame_annotation_filter.collection_ids if frame_annotation_filter else None,
        include_unannotated_samples=True,
    )
    return sample_resolver.count_unannotated_samples(
        session=session,
        collection_id=collection_id,
        grid_filter=video_filter or VideoFilter(),
        unannotated_filter=VideoFilter(frame_annotation_filter=annotations_filter),
    )
