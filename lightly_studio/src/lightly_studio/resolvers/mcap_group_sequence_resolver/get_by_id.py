"""Implementation of get_by_id for MCAP group sequences."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable


def get_by_id(session: Session, sample_id: UUID) -> McapGroupSequenceTable | None:
    """Retrieve the MCAP specialisation for a sequence, if it has one."""
    return session.exec(
        select(McapGroupSequenceTable).where(McapGroupSequenceTable.sample_id == sample_id)
    ).one_or_none()
