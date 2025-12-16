"""Implementation of update collection resolver function."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.resolvers.collection_resolver.get_by_id import get_by_id


def update(
    session: Session, dataset_id: UUID, collection_input: CollectionCreate
) -> CollectionTable:
    """Update an existing collection."""
    collection = get_by_id(session=session, dataset_id=dataset_id)
    if not collection:
        raise ValueError(f"collection ID was not found '{dataset_id}'.")

    collection.name = collection_input.name
    collection.updated_at = datetime.now(timezone.utc)

    session.commit()
    session.refresh(collection)
    return collection
