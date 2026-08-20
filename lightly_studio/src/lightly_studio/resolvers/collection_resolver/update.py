"""Implementation of update collection resolver function."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, CollectionTable
from lightly_studio.resolvers.collection_resolver.get_by_id import get_by_id
from lightly_studio.resolvers.collection_resolver.get_by_name import get_by_name


def update(
    session: Session, collection_id: UUID, collection_input: CollectionCreate
) -> CollectionTable:
    """Update an existing collection.

    Raises:
        ValueError:
            If the collection does not exist, or if a sibling collection already uses
            the new name.
    """
    collection = get_by_id(session=session, collection_id=collection_id)
    if not collection:
        raise ValueError(f"collection ID was not found '{collection_id}'.")

    existing = get_by_name(
        session=session,
        name=collection_input.name,
        parent_collection_id=collection.parent_collection_id,
    )
    if existing is not None and existing != collection_id:
        raise ValueError(
            f"A collection named '{collection_input.name}' already exists. Names must be "
            f"unique among sibling collections. Choose a different name."
        )

    collection.name = collection_input.name
    collection.updated_at = datetime.now(timezone.utc)

    try:
        session.commit()
    except IntegrityError:
        # Only reachable if a concurrent transaction took the name after the check
        # above. Roll back so that the session stays usable.
        session.rollback()
        raise
    session.refresh(collection)
    return collection
