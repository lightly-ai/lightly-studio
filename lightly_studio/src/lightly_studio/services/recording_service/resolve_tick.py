"""Resolves one tick of an MCAP sequence to its recording and channel locators."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap import McapTable
from lightly_studio.models.mcap_group_component_definition import McapDataType
from lightly_studio.models.sequence import SampleSequenceLinkTable
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    sample_resolver,
    sequence_resolver,
)


@dataclass(frozen=True)
class ResolvedTick:
    """One tick of an MCAP sequence.

    Attributes:
        recording_id: The recording the sequence was read from.
        link: The link of the tick's group sample to the sequence.
        channels: The MCAP locator and data type of each channel of the tick, keyed by
            component name, e.g. `front`.
    """

    recording_id: UUID
    link: SampleSequenceLinkTable
    channels: dict[str, tuple[McapTable, McapDataType]]


def resolve_tick(
    session: Session, dataset_id: UUID, sequence_id: UUID, seq_number: int
) -> ResolvedTick | None:
    """Returns the recording and the channel locators of one tick.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick.

    Returns:
        The tick, or `None` if the sequence does not exist, does not belong to
        `dataset_id`, or has no tick at `seq_number`.
    """
    mcap_sequence = mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id)
    if mcap_sequence is None:
        return None
    sample = sample_resolver.get_by_id(session=session, sample_id=sequence_id)
    if sample is None:
        return None
    collection = collection_resolver.get_by_id(session=session, collection_id=sample.collection_id)
    if collection is None or collection.dataset_id != dataset_id:
        return None
    link = sequence_resolver.get_sample_link(
        session=session, sequence_sample_id=sequence_id, seq_number=seq_number
    )
    if link is None:
        return None
    return ResolvedTick(
        recording_id=mcap_sequence.recording_id,
        link=link,
        channels=mcap_resolver.get_tick_channels(session=session, group_sample_id=link.sample_id),
    )
