"""Implementation of get collection by name resolver function."""

from __future__ import annotations

from sqlmodel import Session, select

from lightly_studio.models.collection import CollectionTable


def get_by_name(session: Session, name: str) -> CollectionTable | None:
    """Retrieve a single collection by name."""
    return session.exec(select(CollectionTable).where(CollectionTable.name == name)).one_or_none()
