"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.interfaces import LoaderOption
from sqlmodel import Session, col, func, select

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.group import GroupTable, GroupView, GroupViewsWithCount
from lightly_studio.models.image import ImageTable, ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoTable, VideoView
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter


def get_all(
    session: Session,
    pagination: Paginated | None,
    filters: GroupFilter | None,
) -> GroupViewsWithCount:
    """Retrieve groups ordered by creation time.

    Groups are returned in ascending order by created_at timestamp, and all similarity
    scores in the response are set to None.

    Args:
        session: Database session for executing queries.
        pagination: Optional pagination parameters (offset and limit) for results.
        filters: Optional GroupFilter instance to apply additional filtering criteria.

    Returns:
        GroupViewsWithCount containing:
        - samples: List of GroupView objects with similarity_score set to None
        - total_count: Total number of groups matching the query (before pagination)
        - next_cursor: Cursor for pagination to fetch the next page of results
    """
    load_options = _get_load_options()

    samples_query = select(GroupTable).options(load_options).join(GroupTable.sample)

    total_count_query = select(func.count()).select_from(GroupTable).join(GroupTable.sample)

    if filters:
        samples_query = filters.apply(samples_query)
        total_count_query = filters.apply(total_count_query)

    samples_query = samples_query.order_by(col(SampleTable.created_at).asc())

    if pagination is not None:
        samples_query = samples_query.offset(pagination.offset).limit(pagination.limit)

    total_count = session.exec(total_count_query).one()
    samples = session.exec(samples_query).all()

    # Fetch first sample (image or video) for each group
    group_sample_ids = [group.sample_id for group in samples]
    first_images = _get_first_images_for_groups(session, group_sample_ids)
    first_videos = _get_first_videos_for_groups(session, group_sample_ids)

    group_views = [
        GroupView(
            sample_id=group.sample_id,
            sample=SampleView.model_validate(group.sample),
            similarity_score=None,
            first_sample_image=first_images.get(group.sample_id),
            first_sample_video=first_videos.get(group.sample_id),
        )
        for group in samples
    ]

    return GroupViewsWithCount(
        samples=group_views,
        total_count=total_count,
        next_cursor=_compute_next_cursor(pagination=pagination, total_count=total_count),
    )


def _get_load_options() -> LoaderOption:
    """Get common load options for the sample relationship."""
    return selectinload(GroupTable.sample).options(
        joinedload(SampleTable.tags),
        # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
        joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
        selectinload(SampleTable.captions),
    )


def _compute_next_cursor(
    pagination: Paginated | None,
    total_count: int,
) -> int | None:
    """Compute next cursor for pagination."""
    if pagination and pagination.offset + pagination.limit < total_count:
        return pagination.offset + pagination.limit
    return None


def _get_first_images_for_groups(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, ImageView]:
    """Get the first image sample for each group.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to fetch first images for.

    Returns:
        Dictionary mapping group sample_id to ImageView of the first image in that group.
    """
    if not group_sample_ids:
        return {}

    # Import here to avoid circular dependency
    from lightly_studio.models.group import SampleGroupLinkTable

    # For each group, get the first image sample
    # Join SampleGroupLinkTable to get samples in each group, then join ImageTable
    query = (
        select(SampleGroupLinkTable.parent_sample_id, ImageTable)
        .join(ImageTable, ImageTable.sample_id == SampleGroupLinkTable.sample_id)
        .join(ImageTable.sample)
        .options(
            selectinload(ImageTable.sample).options(
                joinedload(SampleTable.tags),
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
                selectinload(SampleTable.annotations).options(
                    joinedload(AnnotationBaseTable.annotation_label),
                    joinedload(AnnotationBaseTable.object_detection_details),
                    joinedload(AnnotationBaseTable.segmentation_details),
                ),
            )
        )
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .order_by(col(SampleTable.created_at).asc())
    )

    results = session.exec(query).all()

    # Keep only the first image for each group
    first_images: dict[UUID, ImageView] = {}
    for parent_sample_id, image in results:
        if parent_sample_id not in first_images:
            first_images[parent_sample_id] = ImageView(
                sample_id=image.sample_id,
                file_name=image.file_name,
                file_path_abs=image.file_path_abs,
                width=image.width,
                height=image.height,
                sample=SampleView.model_validate(image.sample),
                annotations=[],
                tags=[],
                metadata_dict=None,
                captions=[],
            )

    return first_images


def _get_first_videos_for_groups(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, VideoView]:
    """Get the first video sample for each group.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to fetch first videos for.

    Returns:
        Dictionary mapping group sample_id to VideoView of the first video in that group.
    """
    if not group_sample_ids:
        return {}

    # Import here to avoid circular dependency
    from lightly_studio.models.group import SampleGroupLinkTable

    # For each group, get the first video sample
    query = (
        select(SampleGroupLinkTable.parent_sample_id, VideoTable)
        .join(VideoTable, VideoTable.sample_id == SampleGroupLinkTable.sample_id)
        .join(VideoTable.sample)
        .options(
            selectinload(VideoTable.sample).options(
                joinedload(SampleTable.tags),
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            )
        )
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .order_by(col(SampleTable.created_at).asc())
    )

    results = session.exec(query).all()

    # Keep only the first video for each group
    first_videos: dict[UUID, VideoView] = {}
    for parent_sample_id, video in results:
        if parent_sample_id not in first_videos:
            first_videos[parent_sample_id] = VideoView(
                sample_id=video.sample_id,
                file_name=video.file_name,
                file_path_abs=video.file_path_abs,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
                sample=SampleView.model_validate(video.sample),
            )

    return first_videos
