"""Implementation of get_names_by_ids function for tags."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.tag import TagTable


def get_names_by_ids(session: Session, tag_ids: Sequence[UUID]) -> dict[UUID, str]:
    """Return ``{tag_id: name}`` for the requested tags."""
    if not tag_ids:
        return {}
    stmt = select(TagTable.tag_id, TagTable.name).where(
        db_array.in_array(column=col(TagTable.tag_id), values=tag_ids)
    )
    return dict(session.exec(stmt).all())
