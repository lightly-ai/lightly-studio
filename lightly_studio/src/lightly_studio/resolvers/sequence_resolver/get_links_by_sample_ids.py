"""Get the sequence links of samples."""

from __future__ import annotations

from collections.abc import Collection
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_links_by_sample_ids(
    session: Session, sample_ids: Collection[UUID]
) -> dict[UUID, SampleSequenceLinkTable]:
    """Return the sequence link of each sample that is in a sequence, by sample ID."""
    if not sample_ids:
        return {}
    statement = select(SampleSequenceLinkTable).where(
        col(SampleSequenceLinkTable.sample_id).in_(sample_ids)
    )
    return {link.sample_id: link for link in session.exec(statement).all()}
