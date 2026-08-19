"""Implementation of get_by_name function for tags."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.tag import TagTable


def get_by_name(session: Session, tag_name: str, collection_id: UUID | None) -> TagTable | None:
    """Retrieve a single tag by name."""
    if collection_id:
        return session.exec(
            select(TagTable)
            .where(TagTable.collection_id == collection_id)
            .where(TagTable.name == tag_name)
        ).one_or_none()
    return session.exec(select(TagTable).where(TagTable.name == tag_name)).one_or_none()
