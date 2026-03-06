"""Implementation of get_all_by_collection_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import (
    VideoFrameTable,
    VideoTable,
    VideoView,
    VideoViewsWithCount,
)
from lightly_studio.resolvers.similarity_utils import (
    apply_similarity_join,
    distance_to_similarity,
    get_distance_expression,
)
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter


def _get_load_options() -> list[LoaderOption]:
    """Get common load options for video and frame relationships."""
    return [
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


def _build_min_frame_subquery() -> Any:
    """Build subquery to get minimum frame number per video."""
    return (
        select(
            VideoFrameTable.parent_sample_id,
            func.min(col(VideoFrameTable.frame_number)).label("min_frame_number"),
        )
        .group_by(col(VideoFrameTable.parent_sample_id))
        .subquery()
    )


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute next cursor for pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    sample_ids: list[UUID] | None = None,
    filters: VideoFilter | None = None,
    text_embedding: list[float] | None = None,
) -> VideoViewsWithCount:
    """Retrieve samples for a specific collection with optional filtering."""
    embedding_model_id, distance_expr = get_distance_expression(
        session=session,
        collection_id=collection_id,
        text_embedding=text_embedding,
    )

    if distance_expr is not None and embedding_model_id is not None:
        return _get_all_with_similarity(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            distance_expr=distance_expr,
            pagination=pagination,
            sample_ids=sample_ids,
            filters=filters,
        )
    return _get_all_without_similarity(
        session=session,
        collection_id=collection_id,
        pagination=pagination,
        sample_ids=sample_ids,
        filters=filters,
    )


def _get_all_with_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    embedding_model_id: UUID,
    distance_expr: ColumnElement[float],
    pagination: Paginated | None,
    sample_ids: list[UUID] | None,
    filters: VideoFilter | None,
) -> VideoViewsWithCount:
    """Get videos with similarity search - returns (VideoTable, VideoFrameTable, float) tuples."""
    load_options = _get_load_options()
    min_frame_subquery = _build_min_frame_subquery()

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
        .options(*load_options)
    )
    samples_query = apply_similarity_join(
        query=samples_query,
        sample_id_column=col(VideoTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    total_count_query = (
        select(func.count())
        .select_from(VideoTable)
        .join(VideoTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )
    total_count_query = apply_similarity_join(
        query=total_count_query,
        sample_id_column=col(VideoTable.sample_id),
        embedding_model_id=embedding_model_id,
    )

    if sample_ids:
        samples_query = samples_query.where(col(VideoTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(VideoTable.sample_id).in_(sample_ids))

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    samples_query = samples_query.order_by(distance_expr)

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    video_views = [
        VideoView.from_video_table(
            video=r[0],
            frame=r[1],
            similarity_score=distance_to_similarity(r[2]),
        )
        for r in results
    ]

    return VideoViewsWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
    )


def _get_all_without_similarity(
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    sample_ids: list[UUID] | None,
    filters: VideoFilter | None,
) -> VideoViewsWithCount:
    """Get videos without similarity search - returns (VideoTable, VideoFrameTable) tuples."""
    load_options = _get_load_options()
    min_frame_subquery = _build_min_frame_subquery()

    samples_query = (
        select(VideoTable, VideoFrameTable)
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

    total_count_query = (
        select(func.count())
        .select_from(VideoTable)
        .join(VideoTable.sample)
        .where(SampleTable.collection_id == collection_id)
    )

    if sample_ids:
        samples_query = samples_query.where(col(VideoTable.sample_id).in_(sample_ids))
        total_count_query = total_count_query.where(col(VideoTable.sample_id).in_(sample_ids))

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    samples_query = samples_query.order_by(col(VideoTable.file_path_abs).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    video_views = [
        VideoView.from_video_table(video=video, frame=first_frame) for video, first_frame in results
    ]

    return VideoViewsWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
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
