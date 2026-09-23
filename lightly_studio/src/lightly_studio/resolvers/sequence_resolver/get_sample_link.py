"""Implementation of get_sample_link for a single sequence tick."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_sample_link(
    session: Session, sequence_sample_id: UUID, seq_number: int
) -> SampleSequenceLinkTable | None:
    """Return the link at one position of a sequence.

    Args:
        session: The database session.
        sequence_sample_id: The sample ID of the sequence.
        seq_number: The zero-based position of the tick within the sequence.

    Returns:
        The link at ``seq_number``, or ``None`` if the sequence has no tick there.
    """
    statement = select(SampleSequenceLinkTable).where(
        col(SampleSequenceLinkTable.sequence_sample_id) == sequence_sample_id,
        col(SampleSequenceLinkTable.seq_number) == seq_number,
    )
    return session.exec(statement).one_or_none()
