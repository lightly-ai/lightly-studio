"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers.image_resolver.get_many_by_id import (
    get_many_by_id as get_images_by_id,
)
from lightly_studio.resolvers.video_resolver.get_many_by_id import (
    get_many_by_id as get_videos_by_id,
)


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

    # Get child sample IDs with their parent mapping, ordered by creation time
    # SampleGroupLinkTable establishes many-to-many relationship between groups (parent_sample_id)
    # and their member samples (sample_id). We join with SampleTable to get metadata like
    # collection_id and created_at for ordering.
    link_query = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            SampleGroupLinkTable.sample_id,
            col(SampleTable.collection_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .order_by(col(SampleTable.created_at).asc())
    )
    links = session.exec(link_query).all()

    # Build mappings
    child_to_parent: dict[UUID, UUID] = {}
    collection_to_samples: dict[UUID, list[UUID]] = {}
    for parent_id, child_id, collection_id in links:
        child_to_parent[child_id] = parent_id
        if collection_id not in collection_to_samples:
            collection_to_samples[collection_id] = []
        collection_to_samples[collection_id].append(child_id)

    snapshots: dict[UUID, ImageView | VideoView] = {}

    # Fetch all images by their sample IDs
    all_child_ids = list(child_to_parent.keys())
    images = get_images_by_id(session=session, sample_ids=all_child_ids)

    # Map images to their parent groups (first image per group)
    for image in images:
        parent_id = child_to_parent[image.sample_id]
        if parent_id not in snapshots:
            snapshots[parent_id] = ImageView(
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

    # For groups without images, try videos
    groups_without_images = [gid for gid in group_sample_ids if gid not in snapshots]
    if groups_without_images:
        # Get child IDs for groups without images
        child_ids_without_images = [
            child_id
            for child_id, parent_id in child_to_parent.items()
            if parent_id in groups_without_images
        ]

        # Fetch videos by their sample IDs
        videos = get_videos_by_id(session=session, sample_ids=child_ids_without_images)

        # Map videos to their parent groups (first video per group)
        for video in videos:
            parent_id = child_to_parent[video.sample_id]
            if parent_id not in snapshots:
                snapshots[parent_id] = VideoView(
                    sample_id=video.sample_id,
                    file_name=video.file_name,
                    file_path_abs=video.file_path_abs,
                    width=video.width,
                    height=video.height,
                    fps=video.fps,
                    duration_s=video.duration_s,
                    sample=SampleView.model_validate(video.sample),
                    annotations=[],
                    tags=[],
                    metadata_dict=None,
                    captions=[],
                )

    return snapshots
