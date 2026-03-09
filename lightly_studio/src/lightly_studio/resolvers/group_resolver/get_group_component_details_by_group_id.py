"""Implementation of get_group_component_details_by_ids for group resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, ComponentCollectionView
from lightly_studio.models.group import GroupComponentView
from lightly_studio.resolvers import group_resolver, image_resolver, video_resolver


def get_group_component_details_by_group_id(
    session: Session, group_id: UUID
) -> list[GroupComponentView]:
    """Get group component details for a specific group ID.

    Args:
        session: Database session.
        group_id: Group ID (primary key from the group table).

    Returns:
        List of GroupComponentView objects with component names and media information.
    """
    samples = group_resolver.get_group_components_by_group_id(session=session, group_id=group_id)
    sample_ids = [sample.sample_id for sample in samples]
    images = image_resolver.get_many_by_id(session=session, sample_ids=sample_ids)
    videos = video_resolver.get_many_by_id(session=session, sample_ids=sample_ids)

    # Fetch all unique collection IDs
    collection_ids = {image.sample.collection_id for image in images} | {
        video.sample.collection_id for video in videos
    }

    # Fetch all collections at once
    collections = session.exec(
        select(CollectionTable).where(col(CollectionTable.collection_id).in_(collection_ids))
    ).all()
    collection_id_to_view = {
        collection.collection_id: ComponentCollectionView.from_collection_table(
            collection=collection
        )
        for collection in collections
    }

    # Create a mapping from sample_id to GroupComponentView
    sample_id_to_component: dict[UUID, GroupComponentView] = {}

    # Process images
    for image in images:
        collection_view = collection_id_to_view.get(image.sample.collection_id)
        if collection_view:
            sample_id_to_component[image.sample_id] = GroupComponentView.from_image_table(
                image=image, collection=collection_view
            )

    # Process videos
    for video in videos:
        collection_view = collection_id_to_view.get(video.sample.collection_id)
        if collection_view:
            sample_id_to_component[video.sample_id] = GroupComponentView.from_video_table(
                video=video, collection=collection_view
            )

    # Return list in the same order as input sample_ids
    return [
        sample_id_to_component[sample_id]
        for sample_id in sample_ids
        if sample_id in sample_id_to_component
    ]
