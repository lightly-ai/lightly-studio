"""Service functions for the per-tick details of an MCAP sequence."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_ticks import TickChannelView, TickDetailView
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_sequence_resolver,
    mcap_resolver,
    sample_resolver,
    sequence_resolver,
)


def get_tick_details(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    seq_number: int,
) -> TickDetailView | None:
    """Return the tick details for one tick of a sequence.

    The tick is identified by `sequence_id` and `seq_number`, and the details
    hold the MCAP locators for every channel of that tick.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick to fetch.

    Returns:
        The tick detail, or `None` if the sequence does not exist, does not belong
        to `dataset_id`, or has no tick at `seq_number`.
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

    channel_mcaps = mcap_resolver.get_tick_channels(session=session, group_sample_id=link.sample_id)
    return TickDetailView(
        recording_id=mcap_sequence.recording_id,
        seq_number=link.seq_number,
        timestamp_ns=link.timestamp_ns,
        channels={
            name: TickChannelView.from_mcap_table(mcap=mcap, group_component_name=name)
            for name, mcap in channel_mcaps.items()
        },
    )
