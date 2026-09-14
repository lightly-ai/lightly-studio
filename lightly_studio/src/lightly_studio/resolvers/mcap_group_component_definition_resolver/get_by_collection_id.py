"""Implementation of get_by_collection_id for MCAP group component definitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, select

from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
)


def get_by_collection_id(
    session: Session, collection_id: UUID
) -> McapGroupComponentDefinitionTable | None:
    """Retrieve the MCAP group component definition for a collection.

    Returns None if the generic slot has no MCAP row (classic IMAGE/VIDEO groups).
    """
    return session.exec(
        select(McapGroupComponentDefinitionTable).where(
            McapGroupComponentDefinitionTable.collection_id == collection_id
        )
    ).one_or_none()
