"""Implementation of get_by_id function for mcap samples."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.mcap import McapTable


def get_by_id(session: Session, sample_id: UUID) -> McapTable | None:
    """Retrieve a single mcap sample by ID."""
    return session.exec(select(McapTable).where(McapTable.sample_id == sample_id)).one_or_none()
