"""Find a video by its id."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable


def get_by_id(session: Session, sample_id: UUID, dataset_id: UUID) -> VideoTable | None:
    """Retrieve a video for a given dataset ID by its ID.

    Parameters:
    -----------

    dataset_id : UUID
        The ID of the dataset to retrieve videos for.
    sample_id : UUID
        The ID of the video to retrieve.

    Return:
    -------
        A video object or none.
    """
    query = (
        select(VideoTable)
        .join(VideoTable.sample)
        .where(
            VideoTable.sample_id == sample_id,
            SampleTable.dataset_id == dataset_id,
        )
    )
    return session.exec(query).one()
