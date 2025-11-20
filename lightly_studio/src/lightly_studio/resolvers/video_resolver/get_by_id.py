"""Find a video by its id."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import joinedload, selectinload
from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.video import VideoTable


def get_by_id(session: Session, sample_id: UUID) -> VideoTable | None:
    """Retrieve a video for a given dataset ID by its ID.

    Args:
        session: The database session.
        sample_id: The ID of the video to retrieve.

    Returns:
        A video object or none.
    """
    query = (
        select(VideoTable)
        .where(VideoTable.sample_id == sample_id)
        .options(
            selectinload(VideoTable.sample).options(
                joinedload(SampleTable.tags),
                # Ignore type checker error below as it's a false positive caused by TYPE_CHECKING.
                joinedload(SampleTable.metadata_dict),  # type: ignore[arg-type]
                selectinload(SampleTable.captions),
            ),
        )
    )
    return session.exec(query).one()
