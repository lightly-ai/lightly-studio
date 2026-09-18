"""Query the first indexed keyframe time for each MCAP channel in a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_initial_keyframe_log_time_ns_by_channel(
    session: Session, sequence_id: UUID, channel_ids: list[int]
) -> dict[int, int | None]:
    """Return the earliest indexed keyframe log time for each requested channel."""
    if not channel_ids:
        return {}

    rows = session.exec(
        select(
            col(McapTable.channel_id),
            func.min(col(McapTable.keyframe_log_time_ns)),
        )
        .join(
            SampleSequenceLinkTable,
            col(McapTable.sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(McapTable.channel_id).in_(channel_ids),
        )
        .group_by(col(McapTable.channel_id))
    ).all()
    return dict(rows)
