"""Implementation of delete collection resolver function."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
)
from lightly_studio.resolvers import collection_resolver


def delete(session: Session, collection_id: UUID) -> bool:
    """Delete a collection."""
    collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
    if not collection:
        return False

    if collection.group_component_definition is not None:
        # MCAP extension first: FK to group_component_definition.
        mcap_definition = session.get(McapGroupComponentDefinitionTable, collection_id)
        if mcap_definition is not None:
            session.delete(mcap_definition)
            # Commit separately: DuckDB rejects deleting a referenced row in the
            # transaction that deleted the referencing one.
            session.commit()
        session.delete(collection.group_component_definition)
        collection.group_component_definition = None
        session.commit()

    session.delete(collection)
    session.commit()
    return True
