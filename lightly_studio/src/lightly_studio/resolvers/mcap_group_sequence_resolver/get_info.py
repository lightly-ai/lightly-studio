"""Read a sequence's recording and MCAP component schema in a single view."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.group_component_definition import GroupComponentDefinitionTable
from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionTable,
    McapGroupComponentDefinitionView,
)
from lightly_studio.models.mcap_group_sequence import (
    McapGroupSequenceInfoView,
    McapGroupSequenceTable,
)
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import SequenceTable


def get_info(session: Session, sample_id: UUID) -> McapGroupSequenceInfoView | None:
    """Returns the recording and MCAP component schema of a sequence.

    Two layers in one response: the recording (the physical bag this sequence's
    ``mcap_group_sequence`` row points at) and the component schema (the slots defined
    on the GROUP collection under this sequence, shared by every sequence of the same
    dataset). Reading it walks the collection tree, not ``sample_sequence_link``, so it
    returns the schema even for a sequence with zero ticks indexed yet.

    Carries no per-tick data: no frame locators, calibration, transforms, or
    prev/next links. Use the group resolver for one tick's details.

    Args:
        session: The database session.
        sample_id: The sequence's sample id (a sequence's identity, same as
            `SequenceTable.sample_id`).

    Returns:
        The sequence's recording and sorted component slots, or `None` if the
        sequence exists but is a classic (non-MCAP) sequence.

    Raises:
        ValueError: If no sequence exists with `sample_id`, if its
            `mcap_group_sequence` row points at a recording that no longer exists, or
            if the sequence's collection does not have exactly one GROUP child.
    """
    if session.get(SequenceTable, sample_id) is None:
        raise ValueError(f"Sequence with sample_id '{sample_id}' does not exist.")

    row = session.exec(
        select(McapGroupSequenceTable, RecordingTable, SampleTable)
        .join(
            RecordingTable,
            col(McapGroupSequenceTable.recording_id) == col(RecordingTable.recording_id),
        )
        .join(
            SampleTable,
            col(McapGroupSequenceTable.sample_id) == col(SampleTable.sample_id),
        )
        .where(col(McapGroupSequenceTable.sample_id) == sample_id)
    ).one_or_none()

    if row is None:
        return None

    _mcap_sequence, recording, sample = row

    group_collection = _get_group_collection(
        session=session, sequence_collection_id=sample.collection_id
    )
    components = _get_components(
        session=session, group_collection_id=group_collection.collection_id
    )

    return McapGroupSequenceInfoView.from_parts(
        sample_id=sample_id, recording=recording, components=components
    )


def _get_group_collection(session: Session, sequence_collection_id: UUID) -> CollectionTable:
    """Returns the single GROUP child of a sequence collection.

    Raises:
        ValueError: If the sequence collection does not exist, or does not have
            exactly one GROUP child.
    """
    statement = select(CollectionTable).where(
        col(CollectionTable.parent_collection_id) == sequence_collection_id,
        col(CollectionTable.sample_type) == SampleType.GROUP,
    )
    group_children = list(session.exec(statement).all())

    parent_exists = session.get(CollectionTable, sequence_collection_id) is not None
    if not parent_exists:
        raise ValueError(f"Collection '{sequence_collection_id}' does not exist.")

    if len(group_children) != 1:
        raise ValueError(
            f"Expected exactly one GROUP child under sequence collection "
            f"'{sequence_collection_id}', found {len(group_children)}."
        )
    return group_children[0]


def _get_components(
    session: Session, group_collection_id: UUID
) -> list[McapGroupComponentDefinitionView]:
    """Returns the MCAP slots of a GROUP collection, sorted by slot index.

    Joins the generic slot naming/ordering to the MCAP-specific metadata by
    `collection_id`. A child collection without an MCAP row (a classic IMAGE/VIDEO
    slot) is not a component and is omitted.
    """
    statement = (
        select(CollectionTable, GroupComponentDefinitionTable, McapGroupComponentDefinitionTable)
        .join(
            GroupComponentDefinitionTable,
            col(CollectionTable.collection_id) == col(GroupComponentDefinitionTable.collection_id),
        )
        .join(
            McapGroupComponentDefinitionTable,
            col(CollectionTable.collection_id)
            == col(McapGroupComponentDefinitionTable.collection_id),
        )
        .where(col(CollectionTable.parent_collection_id) == group_collection_id)
        .order_by(col(GroupComponentDefinitionTable.group_component_index))
    )
    rows = session.exec(statement).all()

    return [
        McapGroupComponentDefinitionView.from_definitions(gcd=gcd, mcap_gcd=mcap_gcd)
        for _collection, gcd, mcap_gcd in rows
    ]
