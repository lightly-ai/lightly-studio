"""Query the point cloud MCAP locators of many group samples."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.database import db_array
from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_component_definition import (
    McapDataType,
    McapGroupComponentDefinitionTable,
)
from lightly_studio.models.sample import SampleTable


def get_point_cloud_mcaps_by_group_sample_ids(
    session: Session, group_sample_ids: Sequence[UUID]
) -> dict[UUID, list[McapTable]]:
    """Return the point cloud locators of each group sample (tick).

    Args:
        session: The database session.
        group_sample_ids: The sample IDs of the groups.

    Returns:
        A mapping from group sample ID to the MCAP locators of its point cloud
        components, ordered by `channel_id`. A group without point cloud locators is
        not in the result.
    """
    if not group_sample_ids:
        return {}
    statement = (
        select(SampleGroupLinkTable.parent_sample_id, McapTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(McapTable.sample_id))
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.sample_id) == col(SampleTable.sample_id),
        )
        .join(
            McapGroupComponentDefinitionTable,
            col(McapGroupComponentDefinitionTable.collection_id) == col(SampleTable.collection_id),
        )
        .where(
            db_array.in_array(
                column=col(SampleGroupLinkTable.parent_sample_id), values=group_sample_ids
            )
        )
        .where(col(McapGroupComponentDefinitionTable.mcap_data_type) == McapDataType.POINT_CLOUD)
        .order_by(col(McapTable.channel_id))
    )
    result: dict[UUID, list[McapTable]] = {}
    for group_sample_id, mcap in session.exec(statement).all():
        result.setdefault(group_sample_id, []).append(mcap)
    return result
