"""Retrieve the parent collection ID for a given collection ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


def get_parent_collection_id(session: Session, collection_id: UUID) -> CollectionTable | None:
    """Retrieve the parent collection for a given collection ID."""
    # Note: the aliasing is done inside the function rather than at the module level, because
    # otherwise SQLAlchemy crashes tests.
    ParentCollection = aliased(CollectionTable)  # noqa: N806
    ChildCollection = aliased(CollectionTable)  # noqa: N806
    return session.exec(
        select(ParentCollection)
        .join(
            ChildCollection,
            col(ChildCollection.parent_collection_id) == col(ParentCollection.collection_id),
        )
        .where(ChildCollection.collection_id == collection_id)
    ).one_or_none()
