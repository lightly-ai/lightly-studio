"""Implementation of get_sample_details for sample resolver."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from pydantic import BaseModel
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.image import ImageView
from lightly_studio.models.sample import SampleView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import image_resolver, video_resolver


class GroupComponentView(BaseModel):
    """GroupComponentView representation."""

    component_name: str
    image: ImageView | None = None
    video: VideoView | None = None


def get_group_component_details_by_ids(
    session: Session, sample_ids: Sequence[UUID]
) -> list[GroupComponentView]:
    """Get group component details for a list of sample IDs.

    Args:
        session: Database session.
        sample_ids: List of GroupComponent IDs (primary keys from the samples table).

    A "GroupComponent" is a sample that has bunch of relationships:
    - Collection relationship (samples.collection_id → collections.collection_id): The component
      belongs to a collection/dataset.
    - Group relationship (via SampleGroupLinkTable): The component is linked to a parent group
      sample through the SampleGroupLinkTable join table, where the component is referenced
      by sample_id and the parent group by parent_sample_id.
    - Content relationship: Each sample's actual content (media file information) is stored in
      either ImageTable or VideoTable, linked via sample_id as a foreign key. A sample_id exists
      in SampleTable and exactly one of ImageTable/VideoTable - never both. ImageTable stores
      image-specific data (file_name, file_path_abs, width, height), while VideoTable stores
      video-specific data (file_name, file_path_abs, width, height, fps, duration_s).

    """
    images = image_resolver.get_many_by_id(session, list(sample_ids))
    videos = video_resolver.get_many_by_id(session, list(sample_ids))

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

        sample_id_to_component[image.sample_id] = GroupComponentView(
            component_name=component_name,
            image=ImageView(
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
            ),
            video=None,
        )

    # Process videos
    for video in videos:
        component_name = collection_id_to_name.get(video.sample.collection_id, "")

        sample_id_to_component[video.sample_id] = GroupComponentView(
            component_name=component_name,
            image=None,
            video=VideoView(
                sample_id=video.sample_id,
                file_name=video.file_name,
                file_path_abs=video.file_path_abs,
                width=video.width,
                height=video.height,
                fps=video.fps,
                duration_s=video.duration_s,
                sample=SampleView.model_validate(video.sample),
            ),
        )

    # Return list in the same order as input sample_ids
    return [
        sample_id_to_component[sample_id]
        for sample_id in sample_ids
        if sample_id in sample_id_to_component
    ]
