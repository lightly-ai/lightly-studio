"""Service functions for MCAP sequence tick list and per-tick channel locators."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_ticks import (
    TickChannelView,
    TickDetailView,
    TickListView,
    TickView,
)
from lightly_studio.resolvers import mcap_group_sequence_resolver, mcap_resolver, sequence_resolver


def get_mcap_sequence_ticks(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
) -> TickListView | None:
    """Return the ordered list of ticks for an MCAP sequence.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.

    Returns:
        The tick list, or `None` if the sequence does not exist or does not belong
        to `dataset_id`.
    """
    if not _sequence_belongs_to_dataset(
        session=session, sequence_id=sequence_id, dataset_id=dataset_id
    ):
        return None
    links = sequence_resolver.get_sample_links(session=session, sequence_sample_id=sequence_id)
    return TickListView(
        ticks=[
            TickView(seq_number=link.seq_number, timestamp_ns=link.timestamp_ns) for link in links
        ]
    )


def get_mcap_sequence_tick(
    session: Session,
    dataset_id: UUID,
    sequence_id: UUID,
    seq_number: int,
) -> TickDetailView | None:
    """Return the MCAP locators for every channel of one tick.

    Args:
        session: The database session.
        dataset_id: The dataset the sequence must belong to.
        sequence_id: The sequence sample ID.
        seq_number: The zero-based index of the tick to fetch.

    Returns:
        The tick detail, or `None` if the sequence does not exist, does not belong
        to `dataset_id`, or has no tick at `seq_number`.
    """
    try:
        info = mcap_group_sequence_resolver.get_info(session=session, sample_id=sequence_id)
    except ValueError:
        return None
    if info is None or info.recording.dataset_id != dataset_id:
        return None

    links = sequence_resolver.get_sample_links(session=session, sequence_sample_id=sequence_id)
    link = next((lnk for lnk in links if lnk.seq_number == seq_number), None)
    if link is None:
        return None

    channel_mcaps = mcap_resolver.get_tick_channels(session=session, group_sample_id=link.sample_id)
    return TickDetailView(
        recording_id=info.recording.recording_id,
        seq_number=link.seq_number,
        timestamp_ns=link.timestamp_ns,
        channels={
            name: TickChannelView.from_mcap_table(mcap) for name, mcap in channel_mcaps.items()
        },
    )


def _sequence_belongs_to_dataset(session: Session, sequence_id: UUID, dataset_id: UUID) -> bool:
    try:
        info = mcap_group_sequence_resolver.get_info(session=session, sample_id=sequence_id)
    except ValueError:
        return False
    return info is not None and info.recording.dataset_id == dataset_id
