"""Implementation of create function for tags."""

from __future__ import annotations

from sqlmodel import Session

from lightly_studio.models.tag import TagCreate, TagTable


def create(session: Session, tag: TagCreate) -> TagTable:
    """Create a new tag in the database."""
    db_tag = TagTable.model_validate(tag)
    session.add(db_tag)
    session.commit()
    session.refresh(db_tag)
    return db_tag
