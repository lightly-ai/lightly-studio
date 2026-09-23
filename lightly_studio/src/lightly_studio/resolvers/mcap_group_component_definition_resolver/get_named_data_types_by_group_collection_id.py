"""Implementation of get_named_data_types_by_group_collection_id for MCAP definitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)


def get_named_data_types_by_group_collection_id(
    session: Session, group_collection_id: UUID
) -> list[tuple[str, McapDataType]]:
    """Return the name and the MCAP data type of every slot of a GROUP collection.

    Args:
        session: The database session.
        group_collection_id: The ID of the GROUP collection holding the slots.

    Returns:
        The slots as ``(name, mcap_data_type)`` pairs, ordered by their index. Children
        without an MCAP row, e.g. classic IMAGE/VIDEO slots, are omitted.
    """
    statement = (
        select(
            GroupComponentDefinitionTable.group_component_name,
            McapGroupComponentDefinitionTable.mcap_data_type,
        )
        .join(
            McapGroupComponentDefinitionTable,
            col(GroupComponentDefinitionTable.collection_id)
            == col(McapGroupComponentDefinitionTable.collection_id),
        )
        .join(
            CollectionTable,
            col(GroupComponentDefinitionTable.collection_id) == col(CollectionTable.collection_id),
        )
        .where(col(CollectionTable.parent_collection_id) == group_collection_id)
        .order_by(col(GroupComponentDefinitionTable.group_component_index))
    )
    return [
        (group_component_name, McapDataType(mcap_data_type))
        for group_component_name, mcap_data_type in session.exec(statement).all()
    ]
