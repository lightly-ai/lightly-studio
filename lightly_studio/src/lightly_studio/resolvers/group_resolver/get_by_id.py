"""Implementation of get_by_id function for groups."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.group import GroupTable


def get_by_id(session: Session, sample_id: UUID) -> GroupTable | None:
    """Retrieve a single sample by ID."""
    return session.exec(select(GroupTable).where(GroupTable.sample_id == sample_id)).one_or_none()
