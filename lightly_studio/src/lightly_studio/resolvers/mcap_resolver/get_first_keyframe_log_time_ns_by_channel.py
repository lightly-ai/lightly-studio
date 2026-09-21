"""Query the earliest keyframe_log_time_ns per channel for all channels of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_first_keyframe_log_time_ns_by_channel(
    session: Session, sequence_id: UUID
) -> dict[int, int]:
    """Return the earliest keyframe_log_time_ns for each channel of a sequence.

    Only channels that have at least one tick with a non-null keyframe_log_time_ns
    are included in the result.

    Args:
        session: The database session.
        sequence_id: The sequence's sample_id.

    Returns:
        A mapping from channel_id to the earliest keyframe_log_time_ns for that
        channel. Empty if the sequence has no indexed MCAP ticks with keyframes.
    """
    rows = session.exec(
        select(McapTable.channel_id, func.min(col(McapTable.keyframe_log_time_ns)))
        .where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(McapTable.sample_id) == col(SampleSequenceLinkTable.sample_id),
            col(McapTable.keyframe_log_time_ns).is_not(None),
        )
        .group_by(col(McapTable.channel_id))
    ).all()
    # The is_not(None) filter guarantees min() is non-null for every returned row.
    return {
        channel_id: first_keyframe
        for channel_id, first_keyframe in rows
        if first_keyframe is not None
    }
