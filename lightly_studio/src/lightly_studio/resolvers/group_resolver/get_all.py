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
    group_snapshots = _get_group_snapshots(session, group_sample_ids)
    group_sample_counts = _get_group_sample_counts(session, group_sample_ids)

    group_views = [
        GroupView(
            sample_id=group.sample_id,
            sample=SampleView.model_validate(group.sample),
            similarity_score=None,
            group_snapshot=group_snapshots.get(group.sample_id),
            sample_count=group_sample_counts.get(group.sample_id, 0),
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


def _get_group_snapshots(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, ImageView | VideoView]:
    """Get the first sample (image or video) for each group.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to fetch snapshots for.

    Returns:
        Dictionary mapping group sample_id to ImageView or VideoView of the first
        sample in that group. Images are preferred over videos when both exist.
    """
    if not group_sample_ids:
        return {}

    # Import here to avoid circular dependency
    from lightly_studio.models.group import SampleGroupLinkTable

    # First, try to get images for each group
    image_query = (
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

    image_results = session.exec(image_query).all()

    # Keep only the first image for each group
    snapshots: dict[UUID, ImageView | VideoView] = {}
    for parent_sample_id, image in image_results:
        if parent_sample_id not in snapshots:
            snapshots[parent_sample_id] = ImageView(
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

    # For groups without images, get videos
    groups_without_images = [gid for gid in group_sample_ids if gid not in snapshots]

    if groups_without_images:
        video_query = (
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
            .where(col(SampleGroupLinkTable.parent_sample_id).in_(groups_without_images))
            .order_by(col(SampleTable.created_at).asc())
        )

        video_results = session.exec(video_query).all()

        # Keep only the first video for each group that doesn't have an image
        for parent_sample_id, video in video_results:
            if parent_sample_id not in snapshots:
                snapshots[parent_sample_id] = VideoView(
                    sample_id=video.sample_id,
                    file_name=video.file_name,
                    file_path_abs=video.file_path_abs,
                    width=video.width,
                    height=video.height,
                    duration_s=video.duration_s,
                    fps=video.fps,
                    sample=SampleView.model_validate(video.sample),
                )

    return snapshots


def _get_group_sample_counts(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, int]:
    """Get the count of samples for each group.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to count samples for.

    Returns:
        Dictionary mapping group sample_id to the count of samples in that group.
    """
    if not group_sample_ids:
        return {}

    # Import here to avoid circular dependency
    from lightly_studio.models.group import SampleGroupLinkTable

    # Count samples for each group
    count_query = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            func.count(SampleGroupLinkTable.sample_id).label("sample_count"),
        )
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .group_by(SampleGroupLinkTable.parent_sample_id)
    )

    results = session.exec(count_query).all()

    return dict(results)
