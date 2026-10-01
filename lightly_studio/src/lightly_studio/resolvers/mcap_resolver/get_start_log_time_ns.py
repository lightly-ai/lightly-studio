"""Query the earliest log time across all MCAP ticks of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_start_log_time_ns(session: Session, sequence_id: UUID) -> int | None:
    """Return the smallest log_time_ns across all MCAP ticks of a sequence.

    Args:
        session: The database session.
        sequence_id: The sequence's sample_id.

    Returns:
        The earliest log time in nanoseconds, or `None` if the sequence has no
        indexed MCAP ticks yet.
    """
    result = session.exec(
        select(func.min(col(McapTable.log_time_ns))).where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id,
            col(McapTable.sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
    ).one_or_none()
    return result if result is not None else None
