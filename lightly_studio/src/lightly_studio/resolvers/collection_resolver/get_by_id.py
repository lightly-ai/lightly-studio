"""Implementation of get collection by ID resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.collection import CollectionTable


def get_by_id(session: Session, collection_id: UUID) -> CollectionTable | None:
    """Retrieve a single collection by ID."""
    return session.exec(
        select(CollectionTable).where(CollectionTable.collection_id == collection_id)
    ).one_or_none()
