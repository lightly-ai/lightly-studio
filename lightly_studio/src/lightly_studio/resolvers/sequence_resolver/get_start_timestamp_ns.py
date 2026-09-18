"""Query the earliest timestamp_ns across all slots of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func
from sqlmodel import Session, col, select

from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_start_timestamp_ns(session: Session, sequence_id: UUID) -> int | None:
    """Return the smallest timestamp_ns across all slots of a sequence.

    Args:
        session: The database session.
        sequence_id: The sequence's sample_id.

    Returns:
        The earliest slot timestamp in nanoseconds, or `None` if no slot has a
        timestamp or the sequence holds no samples.
    """
    return session.exec(
        select(func.min(col(SampleSequenceLinkTable.timestamp_ns))).where(
            col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id
        )
    ).one_or_none()
