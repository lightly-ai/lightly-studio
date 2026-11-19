"""Implementation of get_tag_links for sequences."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTagLinkTable
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.models.tag import TagTable


def get_tag_links(session: Session, sequence_sample_id: UUID) -> list[tuple[TagTable, int]]:
    """Return the tags on the samples of a sequence, with the slot of each tagged sample.

    Args:
        session: The database session.
        sequence_sample_id: The sample ID of the sequence.

    Returns:
        One `(tag, seq_number)` pair per tagged sample of the sequence, ordered by tag
        name, then by ``seq_number``. Tags on the sequence sample itself are not included.
    """
    statement = (
        select(TagTable, SampleSequenceLinkTable.seq_number)
        .join(SampleTagLinkTable, col(SampleTagLinkTable.tag_id) == col(TagTable.tag_id))
        .join(
            SampleSequenceLinkTable,
            col(SampleSequenceLinkTable.sample_id) == col(SampleTagLinkTable.sample_id),
        )
        .where(col(SampleSequenceLinkTable.sequence_sample_id) == sequence_sample_id)
        .order_by(col(TagTable.name), col(SampleSequenceLinkTable.seq_number))
    )
    return [(tag, seq_number) for tag, seq_number in session.exec(statement).all()]
