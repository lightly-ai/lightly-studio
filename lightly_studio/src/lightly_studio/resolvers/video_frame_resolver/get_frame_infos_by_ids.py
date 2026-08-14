"""Retrieve lightweight video frame info rows by sample ID."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.video import VideoFrameTable


class VideoFrameInfoRow(NamedTuple):
    """A frame's sample ID paired with its position in the parent video.

    Lightweight read result for ``get_frame_infos_by_ids``: only the three columns
    below are loaded, never a full ``VideoFrameTable`` object. Callers that walk
    every frame of a collection would otherwise hydrate one mapped entity per frame.
    """

    sample_id: UUID
    parent_sample_id: UUID
    frame_number: int


def get_frame_infos_by_ids(
    session: Session,
    sample_ids: Sequence[UUID],
) -> list[VideoFrameInfoRow]:
    """Retrieve sample ID, parent video and frame number for the given sample IDs.

    Output order matches the input order. Sample IDs with no matching frame
    are omitted.

    Args:
        session: The database session.
        sample_ids: Frame sample IDs to load.

    Returns:
        Frame info rows, in the same order as ``sample_ids``.
    """
    if not sample_ids:
        return []

    statement = select(
        VideoFrameTable.sample_id,
        VideoFrameTable.parent_sample_id,
        VideoFrameTable.frame_number,
    ).where(db_array.in_array(column=col(VideoFrameTable.sample_id), values=sample_ids))
    row_by_sample_id = {
        sample_id: VideoFrameInfoRow(
            sample_id=sample_id,
            parent_sample_id=parent_sample_id,
            frame_number=frame_number,
        )
        for sample_id, parent_sample_id, frame_number in session.exec(statement).all()
    }
    return [
        row_by_sample_id[sample_id] for sample_id in sample_ids if sample_id in row_by_sample_id
    ]
