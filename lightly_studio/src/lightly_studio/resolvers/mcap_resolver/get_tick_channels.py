"""Query all MCAP locators for a single group sample, keyed by component name."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sample import SampleTable


def get_tick_channels(session: Session, group_sample_id: UUID) -> dict[str, McapTable]:
    """Return the seek locator for each sensor channel in one synchronized group (tick).

    A tick is one moment in time where every sensor was sampled together: a lidar
    sweep paired with the camera frames closest to it. Each channel in the tick is
    one MCAP message — identified by its channel id and log time — that can be
    fetched from the bag without reading the whole file.

    Args:
        session: The database session.
        group_sample_id: The sample ID of the group that represents the tick.

    Returns:
        A mapping from sensor slot name (e.g. ``"front"``, ``"pcl_front"``) to the
        MCAP seek locator for that sensor's message at this tick. Slots with no
        recorded MCAP message are omitted.
    """
    statement = (
        select(GroupComponentDefinitionTable.group_component_name, McapTable)
        .join(SampleTable, col(SampleTable.sample_id) == col(McapTable.sample_id))
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.sample_id) == col(SampleTable.sample_id),
        )
        .join(
            GroupComponentDefinitionTable,
            col(GroupComponentDefinitionTable.collection_id) == col(SampleTable.collection_id),
        )
        .where(col(SampleGroupLinkTable.parent_sample_id) == group_sample_id)
    )
    rows = session.exec(statement).all()
    return dict(rows)
