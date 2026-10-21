"""Get the first camera component of an MCAP sequence collection."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)


def get_first_video_frame_collection_id(
    session: Session,
    sequence_collection_id: UUID,
) -> UUID | None:
    """Get the collection_id of the lowest-indexed VIDEO_FRAME slot in the collection.

    Resolves the camera slot once per collection by finding the VIDEO_FRAME component
    with the smallest ``group_component_index`` in the GROUP child of the SEQUENCE
    collection. Returns ``None`` when no VIDEO_FRAME slot exists.

    Args:
        session: Database session for executing queries.
        sequence_collection_id: The SEQUENCE collection to resolve the camera for.

    Returns:
        The ``collection_id`` of the lowest-indexed VIDEO_FRAME slot, or ``None``.
    """
    group_collection_id = session.exec(
        select(CollectionTable.collection_id)
        .where(col(CollectionTable.parent_collection_id) == sequence_collection_id)
        .where(col(CollectionTable.sample_type) == SampleType.GROUP)
        .limit(1)
    ).first()
    if group_collection_id is None:
        return None
    return session.exec(
        select(McapGroupComponentDefinitionTable.collection_id)
        .join(
            GroupComponentDefinitionTable,
            col(GroupComponentDefinitionTable.collection_id)
            == col(McapGroupComponentDefinitionTable.collection_id),
        )
        .join(
            CollectionTable,
            col(CollectionTable.collection_id)
            == col(McapGroupComponentDefinitionTable.collection_id),
        )
        .where(col(CollectionTable.parent_collection_id) == group_collection_id)
        .where(col(McapGroupComponentDefinitionTable.mcap_data_type) == McapDataType.VIDEO_FRAME)
        .order_by(col(GroupComponentDefinitionTable.group_component_index).asc())
        .limit(1)
    ).first()
