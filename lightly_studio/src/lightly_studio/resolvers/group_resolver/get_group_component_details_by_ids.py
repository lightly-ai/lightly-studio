"""Implementation of get_group_component_details_by_ids for group resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.group import GroupComponentView
from lightly_studio.resolvers import image_resolver, video_resolver


def get_group_component_views_by_ids(
    session: Session, sample_ids: list[UUID]
) -> list[GroupComponentView]:
    """Get group component details for a list of sample IDs.

    Args:
        session: Database session.
        sample_ids: List of GroupComponent IDs (primary keys from the samples table).

    Returns:
        List of GroupComponentView objects with component names and media information.
    """
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
    collection_id_to_name = {
        collection.collection_id: collection.group_component_name or ""
        for collection in collections
    }

    # Create a mapping from sample_id to GroupComponentView
    sample_id_to_component: dict[UUID, GroupComponentView] = {}

    # Process images
    for image in images:
        component_name = collection_id_to_name.get(image.sample.collection_id, "")
        sample_id_to_component[image.sample_id] = GroupComponentView.from_image_table(
            image=image, component_name=component_name
        )

    # Process videos
    for video in videos:
        component_name = collection_id_to_name.get(video.sample.collection_id, "")
        sample_id_to_component[video.sample_id] = GroupComponentView.from_video_table(
            video=video, component_name=component_name
        )

    # Return list in the same order as input sample_ids
    return [
        sample_id_to_component[sample_id]
        for sample_id in sample_ids
        if sample_id in sample_id_to_component
    ]
