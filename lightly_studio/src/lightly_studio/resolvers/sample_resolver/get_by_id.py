"""Implementation of get_by_id for sample resolver."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.sample import SampleTable


def get_by_id(session: Session, sample_id: UUID) -> SampleTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(SampleTable).where(SampleTable.sample_id == sample_id)).one_or_none()
