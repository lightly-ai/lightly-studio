"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import image_resolver, video_resolver, collection_resolver


def get_group_snapshots(
    session: Session,
    group_collection_id: UUID,
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

    component_collections = collection_resolver.get_group_components(
        session=session,
        parent_collection_id=group_collection_id,
    )
    # Find the component with minimal group_component_index
    first_component = min(
        component_collections,
        key=lambda c: c.group_component_index if c.group_component_index is not None else float("inf"),
    )
    first_component_type =  first_component.sample_type

    # Get child sample IDs with their parent mapping, ordered by creation time
    # SampleGroupLinkTable establishes many-to-many relationship between groups (parent_sample_id)
    # and their member samples (sample_id). We join with SampleTable to get metadata like
    # collection_id and created_at for ordering.
    link_query = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            SampleGroupLinkTable.sample_id,
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .where(col(SampleTable.collection_id) == first_component.collection_id)
        .order_by(col(SampleTable.created_at).asc())
    )
    links = session.exec(link_query).all()

    # Build mappings - only keep first child per parent per collection
    # Optimization: Instead of keeping all children (potentially 100+ per group), we only keep
    # the first child from each collection. Since groups typically have 1-2 component collections
    # (e.g., images and videos), this reduces the number of sample IDs we need to query from
    # potentially hundreds per group to just 1-2 per group.
    parent_to_children: dict[UUID, dict[UUID, UUID]] = {}
    for parent_id, child_id, collection_id in links:
        if parent_id not in parent_to_children:
            parent_to_children[parent_id] = {}
        if collection_id not in parent_to_children[parent_id]:
            parent_to_children[parent_id][collection_id] = child_id

    snapshots: dict[UUID, ImageView | VideoView] = {}

    # Fetch all images by their sample IDs
    all_child_ids = [
        child_id
        for children_by_collection in parent_to_children.values()
        for child_id in children_by_collection.values()
    ]
    images = image_resolver.get_many_by_id(session=session, sample_ids=all_child_ids)

    # Map images to their parent groups
    child_to_parent = {
        child_id: parent_id
        for parent_id, children_by_collection in parent_to_children.items()
        for child_id in children_by_collection.values()
    }
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
            for parent_id in groups_without_images
            if parent_id in parent_to_children
            for child_id in parent_to_children[parent_id].values()
        ]

        # Fetch videos by their sample IDs
        videos = video_resolver.get_many_by_id(session=session, sample_ids=child_ids_without_images)

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
