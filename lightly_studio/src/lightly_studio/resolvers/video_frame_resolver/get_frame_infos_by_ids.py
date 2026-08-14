"""Retrieve lightweight video frame info rows by sample ID."""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.video import VideoFrameTable
from lightly_studio.utils import batching


class VideoFrameInfoRow(NamedTuple):
    """A frame's sample ID paired with its position in the parent video."""

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
    row_by_sample_id: dict[UUID, VideoFrameInfoRow] = {}
    # Batch the ids to stay under PostgreSQL's 65,535 bind-parameter limit.
    for batch in batching.batched(items=sample_ids):
        statement = select(
            VideoFrameTable.sample_id,
            VideoFrameTable.parent_sample_id,
            VideoFrameTable.frame_number,
        ).where(col(VideoFrameTable.sample_id).in_(batch))
        row_by_sample_id.update(
            {
                sample_id: VideoFrameInfoRow(
                    sample_id=sample_id,
                    parent_sample_id=parent_sample_id,
                    frame_number=frame_number,
                )
                for sample_id, parent_sample_id, frame_number in session.exec(statement).all()
            }
        )
    return [
        row_by_sample_id[sample_id] for sample_id in sample_ids if sample_id in row_by_sample_id
    ]
