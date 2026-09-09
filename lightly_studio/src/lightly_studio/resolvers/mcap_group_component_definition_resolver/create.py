"""Implementation of create for MCAP group component definitions."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)
from lightly_studio.resolvers import collection_resolver


def create(
    session: Session,
    collection_id: UUID,
    mcap_data_type: McapDataType,
    channel_id: int,
) -> UUID:
    """Create an MCAP group component definition for an existing generic slot.

    Args:
        session: The database session.
        collection_id: The group component definition / child collection ID.
        mcap_data_type: Whether this slot holds video frames or a point cloud.
        channel_id: The MCAP channel id, same as on mcap samples.

    Returns:
        The collection_id of the created row.

    Raises:
        ValueError: If the generic group component definition does not exist, or the
            child collection is not of sample type MCAP.
    """
    definition = session.get(GroupComponentDefinitionTable, collection_id)
    if definition is None:
        raise ValueError(
            f"Group component definition with collection_id '{collection_id}' does not exist."
        )
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.MCAP,
    )
    session.add(
        McapGroupComponentDefinitionTable(
            collection_id=collection_id,
            mcap_data_type=mcap_data_type,
            channel_id=channel_id,
        )
    )
    session.commit()
    return collection_id
