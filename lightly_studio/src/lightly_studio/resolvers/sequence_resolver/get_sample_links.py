"""Implementation of get_sample_links for sequences."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_sample_links(session: Session, sequence_sample_id: UUID) -> list[SampleSequenceLinkTable]:
    """Return the samples of a sequence, ordered by their position in it.

    Args:
        session: The database session.
        sequence_sample_id: The sample ID of the sequence.

    Returns:
        One link per slot of the sequence, ordered by ``seq_number``. Empty if the
        sequence holds no samples or does not exist.
    """
    statement = (
        select(SampleSequenceLinkTable)
        .where(col(SampleSequenceLinkTable.sequence_sample_id) == sequence_sample_id)
        .order_by(col(SampleSequenceLinkTable.seq_number))
    )
    return list(session.exec(statement).all())
