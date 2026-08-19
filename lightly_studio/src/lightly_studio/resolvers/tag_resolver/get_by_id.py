"""Implementation of get_by_id function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.tag import TagTable


def get_by_id(session: Session, tag_id: UUID) -> TagTable | None:
    """Retrieve a single tag by ID."""
    return session.exec(select(TagTable).where(TagTable.tag_id == tag_id)).one_or_none()
