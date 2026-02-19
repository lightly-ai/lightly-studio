"""Get groups ordered by creation time."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, image_resolver, video_resolver


def get_group_previews(
    session: Session,
    group_collection_id: UUID,
    group_sample_ids: list[UUID],
) -> dict[UUID, ImageView | None] | dict[UUID, VideoView | None]:
    """Get the first sample (image or video) for each group.

    Args:
        session: Database session for executing queries.
        group_collection_id: Collection ID of the group collection.
        group_sample_ids: List of group sample IDs to fetch previews for.

    Returns:
        Dictionary mapping group sample_id to ImageView or VideoView of the first
        sample in that group. Images are preferred over videos when both exist.
    """
    component_collections = collection_resolver.get_group_components(
        session=session,
        parent_collection_id=group_collection_id,
    )

    if len(component_collections) == 0:
        raise ValueError("No component collections found for the given group collection.")

    # Find the component with minimal group_component_index.
    first_component = min(
        component_collections.values(),
        key=lambda c: c.group_component_index
        if c.group_component_index is not None
        else float("inf"),
    )
    first_component_type = first_component.sample_type

    # For every group, get the sample in the first component.
    # The result is a list of tuples (sample_id, group_sample_id).
    link_query = (
        select(
            SampleGroupLinkTable.sample_id,
            SampleGroupLinkTable.parent_sample_id,
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .where(col(SampleTable.collection_id) == first_component.collection_id)
    )
    links: Sequence[tuple[UUID, UUID]] = session.exec(link_query).all()
    sample_id_to_group_id: dict[UUID, UUID] = dict(links)

    # Collect all group IDs that are missing from the links and map them to None.
    matched_group_ids = set(sample_id_to_group_id.values())
    unmatched_group_id_to_none = {
        group_id: None for group_id in group_sample_ids if group_id not in matched_group_ids
    }

    if first_component_type == SampleType.IMAGE:
        return (
            get_group_previews_image(
                session=session,
                sample_id_to_group_id=sample_id_to_group_id,
            )
            | unmatched_group_id_to_none
        )
    if first_component_type == SampleType.VIDEO:
        return (
            get_group_previews_video(
                session=session,
                sample_id_to_group_id=sample_id_to_group_id,
            )
            | unmatched_group_id_to_none
        )
    raise ValueError(f"Unsupported sample type for group snapshot: {first_component_type}")


def get_group_previews_image(
    session: Session,
    sample_id_to_group_id: dict[UUID, UUID],
) -> dict[UUID, ImageView]:
    """Get the first image sample for each group."""
    # Fetch all images by their sample IDs
    images = image_resolver.get_many_by_id(
        session=session,
        sample_ids=list(sample_id_to_group_id.keys()),
    )
    return {
        sample_id_to_group_id[image.sample_id]: ImageView(
            sample_id=image.sample_id,
            file_name=image.file_name,
            file_path_abs=image.file_path_abs,
            width=image.width,
            height=image.height,
            sample=SampleView.model_validate(image.sample),
            # TODO(Kondrat, 02/2026): These are not fetched here, decide how to handle.
            annotations=[],
            tags=[],
            metadata_dict=None,
            captions=[],
        )
        for image in images
    }


def get_group_previews_video(
    session: Session,
    sample_id_to_group_id: dict[UUID, UUID],
) -> dict[UUID, VideoView]:
    """Get the first video sample for each group."""
    videos = video_resolver.get_many_by_id(
        session=session,
        sample_ids=list(sample_id_to_group_id.keys()),
    )
    return {
        sample_id_to_group_id[video.sample_id]: VideoView(
            sample_id=video.sample_id,
            file_name=video.file_name,
            file_path_abs=video.file_path_abs,
            width=video.width,
            height=video.height,
            fps=video.fps,
            duration_s=video.duration_s,
            sample=SampleView.model_validate(video.sample),
            # TODO(Kondrat, 02/2026): These are not fetched here, decide how to handle.
            annotations=[],
            tags=[],
            metadata_dict=None,
            captions=[],
        )
        for video in videos
    }
