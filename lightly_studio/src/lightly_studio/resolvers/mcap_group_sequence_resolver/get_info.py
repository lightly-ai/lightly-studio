"""Read a sequence's recording and MCAP component schema in a single view."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import CollectionTable, SampleType
from lightly_studio.models.mcap_group_component_definition import (
    McapGroupComponentDefinitionView,
)
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceInfoView
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_component_definition_resolver,
    recording_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.mcap_group_sequence_resolver.get_by_id import (
    get_by_id as get_mcap_group_sequence_by_id,
)


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

    mcap_sequence = get_mcap_group_sequence_by_id(session=session, sample_id=sample_id)
    if mcap_sequence is None:
        return None

    recording = recording_resolver.get_by_id(
        session=session, recording_id=mcap_sequence.recording_id
    )
    if recording is None:
        raise ValueError(
            f"Recording '{mcap_sequence.recording_id}' is missing for sequence '{sample_id}'."
        )

    sample = sample_resolver.get_by_id(session=session, sample_id=sample_id)
    if sample is None:
        raise ValueError(f"Sample '{sample_id}' is missing for sequence '{sample_id}'.")

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
    sequence_collection = collection_resolver.get_by_id(
        session=session, collection_id=sequence_collection_id
    )
    if sequence_collection is None:
        raise ValueError(f"Collection '{sequence_collection_id}' does not exist.")

    group_children = [
        child for child in sequence_collection.children if child.sample_type == SampleType.GROUP
    ]
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
    component_collections_by_id = {
        child.collection_id: child
        for child in collection_resolver.get_group_components(
            session=session, parent_collection_id=group_collection_id
        ).values()
    }
    mcap_defs = mcap_group_component_definition_resolver.get_all_by_group_collection_id(
        session=session, group_collection_id=group_collection_id
    )

    components = []
    for mcap_def in mcap_defs:
        component_collection = component_collections_by_id.get(mcap_def.collection_id)
        if component_collection is None or component_collection.group_component_definition is None:
            continue
        components.append(
            McapGroupComponentDefinitionView.from_definitions(
                gcd=component_collection.group_component_definition, mcap_gcd=mcap_def
            )
        )
    components.sort(key=lambda component: component.group_component_index)
    return components
