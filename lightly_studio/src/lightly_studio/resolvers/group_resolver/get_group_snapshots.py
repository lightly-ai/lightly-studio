"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, col, select

from lightly_studio.models.annotation.annotation_base import AnnotationBaseTable
from lightly_studio.models.image import ImageTable, ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoTable, VideoView


def get_group_snapshots(
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
        .join(ImageTable, ImageTable.sample_id == SampleGroupLinkTable.sample_id)  # type: ignore[arg-type]
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
            .join(VideoTable, VideoTable.sample_id == SampleGroupLinkTable.sample_id)  # type: ignore[arg-type]
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
