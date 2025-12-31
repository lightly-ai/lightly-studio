"""Implementation of get_all_by_collection_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.frame import build_frame_view
from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.embedding_model import EmbeddingModelTable
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.sample_embedding import SampleEmbeddingTable
from lightly_studio.models.video import (
    VideoFrameTable,
    VideoTable,
    VideoView,
    VideoViewsWithCount,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def _get_distance_expression(
    session: Session,
    collection_id: UUID,
    text_embedding: list[float] | None,
) -> tuple[UUID | None, Any]:
    """Get distance expression for similarity search if text_embedding is provided."""
    if not text_embedding:
        return None, None

    embedding_model_id = session.exec(
        select(EmbeddingModelTable.embedding_model_id)
        .where(EmbeddingModelTable.collection_id == collection_id)
        .limit(1)
    ).first()

    if not embedding_model_id:
        return None, None

    distance_expr = func.list_cosine_distance(
        SampleEmbeddingTable.embedding,
        text_embedding,
    )
    return embedding_model_id, distance_expr


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    sample_ids: list[UUID] | None = None,
    filters: VideoFilter | None = None,
    text_embedding: list[float] | None = None,
) -> VideoViewsWithCount:
    """Retrieve samples for a specific collection with optional filtering."""
    embedding_model_id, distance_expr = _get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    # Subquery to find the minimum frame_number for each video.
    min_frame_subquery = (
        select(
            VideoFrameTable.parent_sample_id,
            func.min(col(VideoFrameTable.frame_number)).label("min_frame_number"),
        )
        .group_by(col(VideoFrameTable.parent_sample_id))
        .subquery()
    )

    # Common query options for loading related data.
    load_options = [
        selectinload(VideoFrameTable.sample).options(
            joinedload(SampleTable.tags),
            # Ignore type checker error - false positive from TYPE_CHECKING.
            joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
            selectinload(SampleTable.captions),
        ),
        selectinload(VideoTable.sample).options(
            joinedload(SampleTable.tags),
            # Ignore type checker error - false positive from TYPE_CHECKING.
            joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
            selectinload(SampleTable.captions),
        ),
    ]

    # TODO(Horatiu, 11/2025): Check if it is possible to optimize this query.
    # Build the samples query. Include distance_expr in select when doing similarity search.
    if distance_expr is not None:
        samples_query = (
            select(VideoTable, VideoFrameTable, distance_expr)
            .join(VideoTable.sample)
            .outerjoin(
                min_frame_subquery,
                min_frame_subquery.c.parent_sample_id == VideoTable.sample_id,
            )
            .outerjoin(
                VideoFrameTable,
                and_(
                    col(VideoFrameTable.parent_sample_id) == col(VideoTable.sample_id),
                    col(VideoFrameTable.frame_number) == min_frame_subquery.c.min_frame_number,
                ),
            )
            .where(SampleTable.collection_id == collection_id)
            .join(
                SampleEmbeddingTable,
                col(VideoTable.sample_id) == col(SampleEmbeddingTable.sample_id),
            )
            .where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)
            .options(*load_options)
        )
    else:
        samples_query = (
            select(VideoTable, VideoFrameTable)  # type: ignore[assignment]
            .join(VideoTable.sample)
            .outerjoin(
                min_frame_subquery,
                min_frame_subquery.c.parent_sample_id == VideoTable.sample_id,
            )
            .outerjoin(
                VideoFrameTable,
                and_(
                    col(VideoFrameTable.parent_sample_id) == col(VideoTable.sample_id),
                    col(VideoFrameTable.frame_number) == min_frame_subquery.c.min_frame_number,
                ),
            )
            .where(SampleTable.collection_id == collection_id)
            .options(*load_options)
        )

    # Build total count query.
    total_count_query = (
        select(func.count())
        .select_from(VideoTable)
        .join(VideoTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    if distance_expr is not None:
        total_count_query = total_count_query.join(
            SampleEmbeddingTable,
            col(VideoTable.sample_id) == col(SampleEmbeddingTable.sample_id),
        ).where(SampleEmbeddingTable.embedding_model_id == embedding_model_id)

    # Apply sample_ids filter.
    if sample_ids:
        samples_query = samples_query.where(col(VideoTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(VideoTable.sample_id).in_(sample_ids))

    # Apply filters.
    if filters:
        samples_query = filters.apply(samples_query)  # type: ignore[type-var]
        total_count_query = filters.apply(total_count_query)

    # Apply ordering.
    if distance_expr is not None:
        samples_query = samples_query.order_by(distance_expr)
    else:
        samples_query = samples_query.order_by(col(VideoTable.file_path_abs).asc())

    # Apply pagination if provided.
    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()

    next_cursor = None
    if pagination and pagination.offset + pagination.limit < total_count:
        next_cursor = pagination.offset + pagination.limit

    # Fetch videos with their first frames and convert to VideoView.
    results = session.exec(samples_query).all()

    # Process results and extract similarity scores if available.
    if distance_expr is not None:
        # Results are tuples of (VideoTable, VideoFrameTable, distance).
        video_views = [
            convert_video_table_to_view(
                video=r[0],
                first_frame=r[1],
                similarity_score=1.0 - r[2],
            )
            for r in results
        ]
    else:
        video_views = [  # type: ignore[misc]
            convert_video_table_to_view(video=video, first_frame=first_frame)
            for video, first_frame in results
        ]

    return VideoViewsWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=next_cursor,
    )


# TODO(Horatiu, 11/2025): This should be deleted when we have proper way of getting all frames for
# a video.
def get_all_by_collection_id_with_frames(
    session: Session,
    collection_id: UUID,
) -> Sequence[VideoTable]:
    """Retrieve video table with all the samples."""
    samples_query = (
        select(VideoTable).join(VideoTable.sample).where(SampleTable.collection_id == collection_id)
    )
    samples_query = samples_query.order_by(col(VideoTable.file_path_abs).asc())
    return session.exec(samples_query).all()


def convert_video_table_to_view(
    video: VideoTable,
    first_frame: VideoFrameTable | None,
    similarity_score: float | None = None,
) -> VideoView:
    """Convert VideoTable to VideoView with only the first frame."""
    first_frame_view = None
    if first_frame:
        first_frame_view = build_frame_view(first_frame)

    return VideoView(
        width=video.width,
        height=video.height,
        duration_s=video.duration_s,
        fps=video.fps,
        file_name=video.file_name,
        file_path_abs=video.file_path_abs,
        sample_id=video.sample_id,
        sample=SampleView.model_validate(video.sample),
        frame=first_frame_view,
        similarity_score=similarity_score,
    )
