"""Retrieve video frames for multiple videos."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.video import VideoFrameTable


def get_all_by_video_ids(
    session: Session,
    video_ids: Sequence[UUID],
) -> Sequence[VideoFrameTable]:
    """Retrieve all video frames for the given video sample IDs.

    The returned frames are ordered by (parent_sample_id, frame_number).
    """
    if not video_ids:
        return []

    stmt = (
        select(VideoFrameTable)
        .where(db_array.in_array(column=col(VideoFrameTable.parent_sample_id), values=video_ids))
        .order_by(
            col(VideoFrameTable.parent_sample_id).asc(), col(VideoFrameTable.frame_number).asc()
        )
    )
    return session.exec(stmt).all()
