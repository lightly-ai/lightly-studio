"""Get groups ordered by creation time."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleTable, SampleView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, image_resolver, video_resolver


def get_group_snapshots(
    session: Session,
    group_collection_id: UUID,
    group_sample_ids: list[UUID],
) -> dict[UUID, ImageView | None] | dict[UUID, VideoView | None]:
    """Get the first sample (image or video) for each group.

    Args:
        session: Database session for executing queries.
        group_collection_id: Collection ID of the group collection.
        group_sample_ids: List of group sample IDs to fetch snapshots for.

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

    # Find the component with minimal group_component_index
    # First component is group of all of the samples
    first_component = min(
        component_collections.values(),
        key=lambda c: c.group_component_index
        if c.group_component_index is not None
        else float("inf"),
    )
    first_component_type = first_component.sample_type

    # Get child sample IDs with their parent mapping, ordered by creation time
    # SampleGroupLinkTable establishes many-to-many relationship between groups (parent_sample_id)
    # and their member samples (sample_id). We join with SampleTable to get metadata like
    # collection_id and created_at for ordering.
    link_query = (
        select(
            SampleGroupLinkTable.parent_sample_id,
            SampleGroupLinkTable.sample_id,
        )
        .outerjoin(SampleTable, col(SampleTable.sample_id) == col(SampleGroupLinkTable.sample_id))
        .where(col(SampleGroupLinkTable.parent_sample_id).in_(group_sample_ids))
        .where(col(SampleTable.collection_id) == first_component.collection_id)
        .order_by(col(SampleTable.created_at).asc())
    )
    # we have here group_id + sample_id
    links = session.exec(link_query).all()

    # `links` is a list of tuples (parent_sample_id, sample_id) ordered by sample creation time.
    group_id_to_sample_id: dict[UUID, UUID | None] = dict(links)

    # Ensure all requested group_sample_ids are present, even if they have no matching samples
    for group_id in group_sample_ids:
        if group_id not in group_id_to_sample_id:
            group_id_to_sample_id[group_id] = None

    if first_component_type == SampleType.IMAGE:
        return get_group_snapshots_image(
            session=session,
            group_id_to_sample_id=group_id_to_sample_id,
        )
    if first_component_type == SampleType.VIDEO:
        return get_group_snapshots_video(
            session=session,
            group_id_to_sample_id=group_id_to_sample_id,
        )
    raise ValueError(f"Unsupported sample type for group snapshot: {first_component_type}")


def get_group_snapshots_image(
    session: Session,
    group_id_to_sample_id: dict[UUID, UUID | None],
) -> dict[UUID, ImageView | None]:
    """Get the first image sample for each group."""
    # Fetch all images by their sample IDs
    images = image_resolver.get_many_by_id(
        session=session,
        sample_ids=[
            sample_id for sample_id in group_id_to_sample_id.values() if sample_id is not None
        ],
    )
    sample_id_to_image = {image.sample_id: image for image in images}

    result: dict[UUID, ImageView | None] = {}
    for group_id, sample_id in group_id_to_sample_id.items():
        if sample_id is None:
            result[group_id] = None
        else:
            image = sample_id_to_image[sample_id]
            result[group_id] = ImageView(
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

    return result


def get_group_snapshots_video(
    session: Session,
    group_id_to_sample_id: dict[UUID, UUID | None],
) -> dict[UUID, VideoView | None]:
    """Get the first video sample for each group."""
    videos = video_resolver.get_many_by_id(
        session=session,
        sample_ids=[
            sample_id for sample_id in group_id_to_sample_id.values() if sample_id is not None
        ],
    )
    sample_id_to_video = {video.sample_id: video for video in videos}

    result: dict[UUID, VideoView | None] = {}
    for group_id, sample_id in group_id_to_sample_id.items():
        if sample_id is None:
            result[group_id] = None
        else:
            video = sample_id_to_video[sample_id]
            result[group_id] = VideoView(
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
    return result
