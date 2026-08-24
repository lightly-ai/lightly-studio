"""Implementation of get_all_by_collection_id function for videos."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, and_
from sqlalchemy import Select as SQLAlchemySelect
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.frame import build_frame_view
from lightly_studio.api.routes.api.validators import Paginated

# Aliased because `order_by` is also a parameter name throughout this module.
from lightly_studio.core.dataset_query import order_by as order_by_module
from lightly_studio.core.dataset_query.order_by import OrderByExpression, OrderByField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.database import db_array
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.sample import SampleTable, SampleView
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


def get_all_by_collection_id(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None = None,
    sample_ids: list[UUID] | None = None,
    filters: VideoFilter | None = None,
    text_embedding: list[float] | None = None,
    order_by: list[OrderByExpression] | None = None,
) -> VideoViewsWithCount:
    """Retrieve samples for a specific collection with optional filtering.

    Similarity search takes precedence over ``order_by``: when ``text_embedding`` is
    given, results are ordered by distance and ``order_by`` is ignored.
    """
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
        order_by=order_by,
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
    order_value: float | None = None,
) -> VideoView:
    """Convert VideoTable to VideoView with only the first frame.

    Args:
        video: The video row to convert.
        first_frame: The video's lowest-numbered frame, used for the thumbnail.
        similarity_score: Similarity to a text/embedding query, when search is active.
        order_value: Primary sort value for the current grid sort, when provided by the
            resolver. Mutually exclusive with ``similarity_score`` for the grid overlay.
    """
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
        order_value=order_value,
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
        samples_query = samples_query.where(
            db_array.in_array(column=col(VideoTable.sample_id), values=sample_ids)
        )
        total_count_query = total_count_query.where(
            db_array.in_array(column=col(VideoTable.sample_id), values=sample_ids)
        )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    # `distance_expr` alone is not a total order: equal distances would let rows move
    # between page requests. `file_path_abs` and `sample_id` close the ordering, matching
    # the tiebreakers `_apply_ordering` applies on the non-similarity path.
    samples_query = samples_query.order_by(
        distance_expr,
        col(VideoTable.file_path_abs).asc(),
        col(VideoTable.sample_id).asc(),
    )

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    results = session.exec(samples_query).all()

    video_views = [
        convert_video_table_to_view(
            video=r[0],
            first_frame=r[1],
            similarity_score=distance_to_similarity(r[2]),
        )
        for r in results
    ]

    return VideoViewsWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
    )


def _get_all_without_similarity(  # noqa: PLR0913
    session: Session,
    collection_id: UUID,
    pagination: Paginated | None,
    sample_ids: list[UUID] | None,
    filters: VideoFilter | None,
    order_by: list[OrderByExpression] | None,
) -> VideoViewsWithCount:
    """Get videos without similarity search - returns (VideoTable, VideoFrameTable) tuples.

    Ordering, including the tiebreakers that make it total, is built by
    ``_apply_ordering``. The primary sort value is returned per row in
    ``VideoView.order_value``; non-numeric values (e.g. strings) become ``None``.
    """
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
        samples_query = samples_query.where(
            db_array.in_array(column=col(VideoTable.sample_id), values=sample_ids)
        )
        total_count_query = total_count_query.where(
            db_array.in_array(column=col(VideoTable.sample_id), values=sample_ids)
        )

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    ordered_query = _apply_ordering(query=samples_query, order_by=order_by)

    if pagination is not None:
        ordered_query = ordered_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    # Multi-column rows: VideoTable at index 0, VideoFrameTable at 1, sort value by label.
    rows = session.execute(ordered_query).all()

    video_views = [
        convert_video_table_to_view(
            video=row[0],
            first_frame=row[1],
            order_value=_coerce_order_value(order_by_module.get_order_value(row=row)),
        )
        for row in rows
    ]

    return VideoViewsWithCount(
        samples=video_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination, total_count),
    )


def _apply_ordering(
    query: SQLAlchemySelect[Any],
    order_by: list[OrderByExpression] | None,
) -> SQLAlchemySelect[Any]:
    """Order the query and append the primary sort value to the SELECT.

    Only the primary expression contributes a value; the rest contribute joins and
    ``ORDER BY`` alone. ``sample_id`` closes the ordering, because neither the requested
    sort nor ``file_path_abs`` is unique and equal rows would otherwise be free to move
    between page requests. It sorts ascending in both directions, mirroring the image
    keyset convention in ``get_adjacent_images_keyset._keyset_sort_keys`` so a sorted
    video prev/next can match this order later. ``get_adjacent_videos`` still ignores the
    sort, so the grid and prev/next do not yet agree.
    """
    expressions = _with_tiebreakers(order_by)
    ordered_query = expressions[0].apply_with_order_value(query)
    for expr in expressions[1:]:
        ordered_query = expr.apply_joins(ordered_query)
        ordered_query = ordered_query.order_by(*expr.to_column_elements())
    return ordered_query.order_by(col(VideoTable.sample_id).asc())


def _with_tiebreakers(order_by: list[OrderByExpression] | None) -> list[OrderByExpression]:
    """Append a ``file_path_abs`` tiebreaker to the requested sort when it is missing.

    Follows the primary sort's direction. Defaults to ``file_path_abs`` ascending when
    nothing was requested.
    """
    if not order_by:
        return [OrderByField(field=VideoSampleField.file_path_abs).asc()]

    # Copy so appending the tiebreaker does not mutate the caller's list.
    order_by = list(order_by)
    if not _file_path_abs_in_order_by(order_by):
        order_by.append(
            OrderByField(field=VideoSampleField.file_path_abs).asc()
            if order_by[0].ascending
            else OrderByField(field=VideoSampleField.file_path_abs).desc()
        )
    return order_by


def _file_path_abs_in_order_by(order_by: list[OrderByExpression]) -> bool:
    return any(
        isinstance(expr, OrderByField) and expr.field is VideoSampleField.file_path_abs
        for expr in order_by
    )


def _coerce_order_value(value: object) -> float | None:
    """Convert a raw SQL sort value to a float suitable for ``VideoView.order_value``.

    Only numeric values are converted; booleans return ``None``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _get_load_options() -> list[LoaderOption]:
    """Get common load options for video and frame relationships."""
    # Eagerly load annotations to avoid multiple queries.
    return [
        selectinload(VideoFrameTable.sample).options(
            joinedload(SampleTable.tags),
            # Ignore type checker error - false positive from TYPE_CHECKING.
            joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
            selectinload(SampleTable.captions),
            selectinload(SampleTable.annotations).options(
                joinedload(AnnotationBaseTable.annotation_label),
                joinedload(AnnotationBaseTable.object_detection_details),
                joinedload(AnnotationBaseTable.segmentation_details),
                selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
            ),
        ),
        selectinload(VideoTable.sample).options(
            joinedload(SampleTable.tags),
            # Ignore type checker error - false positive from TYPE_CHECKING.
            joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
            selectinload(SampleTable.captions),
            # Videos only support classification annotations directly, so there is no need
            # to join object_detection_details or segmentation_details here.
            selectinload(SampleTable.annotations).options(
                joinedload(AnnotationBaseTable.annotation_label),
                selectinload(AnnotationBaseTable.sample).options(selectinload(SampleTable.tags)),
            ),
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
