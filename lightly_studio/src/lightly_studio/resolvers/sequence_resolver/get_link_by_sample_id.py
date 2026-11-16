"""Return the sequence link of a sample."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_link_by_sample_id(session: Session, sample_id: UUID) -> SampleSequenceLinkTable | None:
    """Return the link that places a sample in a sequence.

    Args:
        session: The database session.
        sample_id: The sample, e.g. the tick group an annotation is attached to.

    Returns:
        The link, or `None` if the sample is not part of a sequence.
    """
    return session.get(SampleSequenceLinkTable, sample_id)
