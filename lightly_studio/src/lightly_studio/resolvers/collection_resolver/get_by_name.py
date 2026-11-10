"""Implementation of the get collection by name resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.resolvers import collection_resolver


def get_by_name(
    session: Session,
    name: str,
    parent_collection_id: UUID | None,
) -> UUID | None:
    """Retrieves the ID of a collection by its name and parent collection.

    See `get_table_by_name` for the arguments and the errors.
    """
    collection = collection_resolver.get_table_by_name(
        session=session, name=name, parent_collection_id=parent_collection_id
    )
    return None if collection is None else collection.collection_id
