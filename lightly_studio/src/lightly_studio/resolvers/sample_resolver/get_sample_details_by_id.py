"""Implementation of get_sample_details for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupView
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import group_resolver, image_resolver, sample_resolver, video_resolver


def get_sample_details_by_id(
    session: Session, sample_id: UUID
) -> ImageView | VideoView | GroupView:
    """Retrieve the sample details for a given sample ID.

    Based on the sample type, returns the appropriate table:
    - ImageView for IMAGE samples
    - VideoView for VIDEO samples
    - GroupView for GROUP samples

    Args:
        session: The database session.
        sample_id: The ID of the sample.

    Returns:
        The appropriate view (ImageView, VideoView, or GroupView) for the sample.

    Raises:
        ValueError: If the sample does not exist or has an unsupported type.
    """
    sample_type = sample_resolver.get_sample_type(session, sample_id)

    if sample_type == SampleType.IMAGE:
        images = image_resolver.get_many_by_id(session, [sample_id])
        if not images:
            raise ValueError(f"Image with sample_id '{sample_id}' not found.")
        return image_resolver.get_view_by_id(session=session, sample_id=images[0].sample_id)

    if sample_type == SampleType.VIDEO:
        videos = video_resolver.get_many_by_id(session, [sample_id])
        if not videos:
            raise ValueError(f"Video with sample_id '{sample_id}' not found.")
        video_view = video_resolver.get_view_by_id(session=session, sample_id=videos[0].sample_id)
        if video_view is None:
            raise ValueError(
                f"Video with sample_id '{videos[0].sample_id}' not found for video '{sample_id}'."
            )
        return video_view

    if sample_type == SampleType.GROUP:
        group = group_resolver.get_by_id(session, sample_id)
        if group is None:
            raise ValueError(f"Group with sample_id '{sample_id}' not found.")
        return group_resolver.get_view_by_id(session=session, sample_id=group.sample_id)

    raise ValueError(f"Unsupported sample type '{sample_type}' for sample_id '{sample_id}'.")
