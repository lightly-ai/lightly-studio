"""Retrieve the parent dataset ID for a given dataset ID."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable

ParentDataset = aliased(CollectionTable)
ChildDataset = aliased(CollectionTable)


def get_parent_collection_id(session: Session, collection_id: UUID) -> CollectionTable | None:
    """Retrieve the parent collection for a given collection ID."""
    return session.exec(
        select(ParentDataset)
        .join(
            ChildDataset, col(ChildDataset.parent_collection_id) == col(ParentDataset.collection_id)
        )
        .where(ChildDataset.collection_id == collection_id)
    ).one_or_none()
