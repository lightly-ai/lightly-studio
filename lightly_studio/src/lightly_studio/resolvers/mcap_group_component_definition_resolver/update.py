"""Implementation of update for MCAP group component definitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
)


def update(
    session: Session,
    collection_id: UUID,
    channel_id: int | None = None,
    frame_id: str | None = None,
) -> McapGroupComponentDefinitionTable:
    """Fill the columns of a slot that a recording supplies, first write wins.

    A column that already holds a value keeps it, so indexing a second recording does
    not move a slot to a different channel. A ``None`` argument leaves its column
    untouched.

    Args:
        session: The database session.
        collection_id: The MCAP group component definition ID.
        channel_id: The numeric MCAP channel of the slot. Ignored if already set.
        frame_id: The id that matches the slot against calibration/transform data.
            Empty or whitespace-only values count as no value. Ignored if already set.

    Returns:
        The definition, with the columns this call filled.

    Raises:
        ValueError: If no MCAP group component definition has that collection ID.
    """
    definition = session.get(McapGroupComponentDefinitionTable, collection_id)
    if definition is None:
        raise ValueError(
            f"McapGroupComponentDefinition with collection_id '{collection_id}' does not exist."
        )

    if definition.channel_id is None and channel_id is not None:
        definition.channel_id = channel_id
    stripped_frame_id = frame_id.strip() if frame_id else ""
    if definition.frame_id is None and stripped_frame_id:
        definition.frame_id = stripped_frame_id

    session.add(definition)
    session.commit()
    session.refresh(definition)
    return definition
