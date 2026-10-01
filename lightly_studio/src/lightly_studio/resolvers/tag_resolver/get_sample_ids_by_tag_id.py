"""Implementation of get_sample_ids_by_tag_id function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.sample import SampleTagLinkTable


def get_sample_ids_by_tag_id(session: Session, tag_id: UUID) -> list[UUID]:
    """Return all sample IDs assigned to a tag."""
    statement = select(SampleTagLinkTable.sample_id).where(col(SampleTagLinkTable.tag_id) == tag_id)
    return [sample_id for sample_id in session.exec(statement).all() if sample_id is not None]
