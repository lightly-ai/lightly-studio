"""Implementation of get collection names by IDs resolver function."""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable


def get_names_by_ids(session: Session, collection_ids: Iterable[UUID]) -> dict[UUID, str]:
    """Batch-fetch collection names for the given collection IDs.

    Args:
        session: The database session.
        collection_ids: The collection IDs to look up.

    Returns:
        A mapping from collection ID to collection name. Missing IDs are omitted.
    """
    ids = set(collection_ids)
    if not ids:
        return {}
    collections = session.exec(
        select(CollectionTable).where(col(CollectionTable.collection_id).in_(ids))
    ).all()
    return {c.collection_id: c.name for c in collections}
