"""Retrieve the parent collection ID for a given collection ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable

ParentCollection = aliased(CollectionTable)
ChildCollection = aliased(CollectionTable)


def get_parent_collection_id(session: Session, collection_id: UUID) -> CollectionTable | None:
    """Retrieve the parent collection for a given collection ID."""
    return session.exec(
        select(ParentCollection)
        .join(
            ChildCollection,
            col(ChildCollection.parent_collection_id) == col(ParentCollection.collection_id),
        )
        .where(ChildCollection.collection_id == collection_id)
    ).one_or_none()
