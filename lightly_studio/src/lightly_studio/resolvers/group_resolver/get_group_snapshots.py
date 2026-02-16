"""Get group snapshots."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.image import ImageTable, ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoTable, VideoView


def get_group_snapshots(
    session: Session,
    group_sample_ids: list[UUID],
) -> dict[UUID, ImageView | VideoView]:
    """Get the first sample (image or video) for each group.

    This function efficiently retrieves snapshot previews for groups by:
    1. Using SQL window functions (ROW_NUMBER) to select only the first (oldest)
       sample per group at the database level, avoiding fetching unnecessary data
    2. Prioritizing images over videos - if a group has images, an image is returned
    3. Only loading minimal data (no annotations, tags, or metadata) for performance

    Performance: Uses PARTITION BY to fetch exactly one sample per group instead of
    fetching all samples and filtering in Python, which is significantly faster for
    groups with many samples.

    Args:
        session: Database session for executing queries.
        group_sample_ids: List of group sample IDs to fetch snapshots for.

    Returns:
        Dictionary mapping group sample_id to ImageView or VideoView of the first
        sample in that group. Images are preferred over videos when both exist.
    """
    if not group_sample_ids:
        return {}

    # Use window function to get only the first (oldest) IMAGE per group
    # Images are preferred over videos, so we check for images first
    first_image_subquery = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            SampleGroupLinkTable.sample_id,
            func.row_number()
            .over(
                partition_by=col(SampleGroupLinkTable.parent_sample_id),
                order_by=col(SampleTable.created_at).asc(),
            )
            .label("rn"),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .join(ImageTable, col(ImageTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .subquery()
    )

    # Get images using the subquery (only first IMAGE per group)
    image_query = (
        select(first_image_subquery.c.parent_sample_id, ImageTable, SampleTable)
        .join(ImageTable, col(ImageTable.sample_id) == first_image_subquery.c.sample_id)
        .join(SampleTable, col(SampleTable.sample_id) == col(ImageTable.sample_id))
        .where(first_image_subquery.c.rn == 1)
    )

    image_results = session.exec(image_query).all()

    # Build snapshots from images
    snapshots: dict[UUID, ImageView | VideoView] = {}
    for parent_sample_id, image, sample in image_results:
        snapshots[parent_sample_id] = ImageView(
            sample_id=image.sample_id,
            file_name=image.file_name,
            file_path_abs=image.file_path_abs,
            width=image.width,
            height=image.height,
            sample=SampleView(
                sample_id=sample.sample_id,
                collection_id=sample.collection_id,
                created_at=sample.created_at,
                updated_at=sample.updated_at,
            ),
            annotations=[],
            tags=[],
            metadata_dict=None,
            captions=[],
        )

    # For groups without images, get videos
    groups_without_images = [gid for gid in group_sample_ids if gid not in snapshots]

    if groups_without_images:
        first_video_subquery = (
            select(
                SampleGroupLinkTable.parent_sample_id,
                SampleGroupLinkTable.sample_id,
                func.row_number()
                .over(
                    partition_by=col(SampleGroupLinkTable.parent_sample_id),
                    order_by=col(SampleTable.created_at).asc(),
                )
                .label("rn"),
            )
            .join(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
            .join(VideoTable, col(VideoTable.sample_id) == col(SampleGroupLinkTable.sample_id))
            .where(col(SampleGroupLinkTable.parent_sample_id).in_(groups_without_images))
            .subquery()
        )

        video_query = (
            select(first_video_subquery.c.parent_sample_id, VideoTable, SampleTable)
            .join(VideoTable, col(VideoTable.sample_id) == first_video_subquery.c.sample_id)
            .join(SampleTable, col(SampleTable.sample_id) == col(VideoTable.sample_id))
            .where(first_video_subquery.c.rn == 1)
        )

        video_results = session.exec(video_query).all()

        for parent_sample_id, video, sample in video_results:
            snapshots[parent_sample_id] = VideoView(
                sample_id=video.sample_id,
                file_name=video.file_name,
                file_path_abs=video.file_path_abs,
                width=video.width,
                height=video.height,
                duration_s=video.duration_s,
                fps=video.fps,
                sample=SampleView(
                    sample_id=sample.sample_id,
                    collection_id=sample.collection_id,
                    created_at=sample.created_at,
                    updated_at=sample.updated_at,
                ),
            )

    return snapshots
