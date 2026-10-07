"""Query the MCAP channel id per component for all indexed ticks of a sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.group import SampleGroupLinkTable
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap import McapTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SampleSequenceLinkTable


def get_channel_ids_by_component(session: Session, sequence_id: UUID) -> dict[str, int]:
    """Return the MCAP channel id for each component of a sequence.

    Reads channel ids from the indexed MCAP ticks rather than from the
    dataset-level component schema, so the ids reflect the actual channel
    assignments in the recording file.

    Args:
        session: The database session.
        sequence_id: The sequence's sample_id.

    Returns:
        A mapping from component name to channel id. Empty if the sequence has
        no indexed ticks yet.
    """
    statement = (
        select(
            GroupComponentDefinitionTable.group_component_name,
            McapTable.channel_id,
        )
        .join(
            SampleGroupLinkTable,
            col(SampleGroupLinkTable.sample_id) == col(McapTable.sample_id),
        )
        .join(
            SampleSequenceLinkTable,
            col(SampleGroupLinkTable.parent_sample_id) == col(SampleSequenceLinkTable.sample_id),
        )
        .join(SampleTable, col(SampleTable.sample_id) == col(McapTable.sample_id))
        .join(
            GroupComponentDefinitionTable,
            col(GroupComponentDefinitionTable.collection_id) == col(SampleTable.collection_id),
        )
        .where(col(SampleSequenceLinkTable.sequence_sample_id) == sequence_id)
        .distinct()
    )
    rows = session.exec(statement).all()
    return dict(rows)
