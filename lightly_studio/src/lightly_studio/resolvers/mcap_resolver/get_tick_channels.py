"""Query all MCAP locators for a single group sample, keyed by component name."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sample import SampleTable


def get_tick_channels(session: Session, group_sample_id: UUID) -> dict[str, McapTable]:
    """Return the MCAP locators for every component of a group sample.

    Args:
        session: The database session.
        group_sample_id: The sample ID of the group (tick).

    Returns:
        A mapping from component name to its McapTable row. Components that have
        no MCAP record are omitted.
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
