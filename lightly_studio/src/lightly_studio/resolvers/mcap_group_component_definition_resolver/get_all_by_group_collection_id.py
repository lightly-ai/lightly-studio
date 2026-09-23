"""Implementation of get_all_by_group_collection_id for MCAP group component definitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
)


def get_all_by_group_collection_id(
    session: Session, group_collection_id: UUID
) -> list[McapGroupComponentDefinitionTable]:
    """Return MCAP definitions for child collections of a GROUP collection.

    Children without an MCAP row (classic IMAGE/VIDEO slots) are omitted. Filter the
    result with ``mcap_data_type`` to select e.g. point-cloud slots.
    """
    statement = (
        select(McapGroupComponentDefinitionTable)
        .join(
            CollectionTable,
            col(McapGroupComponentDefinitionTable.collection_id)
            == col(CollectionTable.collection_id),
        )
        .where(col(CollectionTable.parent_collection_id) == group_collection_id)
    )
    return list(session.exec(statement).all())
