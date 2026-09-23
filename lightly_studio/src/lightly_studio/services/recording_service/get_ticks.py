"""Service functions for the MCAP sequence tick list."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.mcap_sequence_ticks import (
    TickListView,
    TickView,
)
from lightly_studio.resolvers import (
    collection_resolver,
    mcap_group_sequence_resolver,
    sample_resolver,
    sequence_resolver,
)


def get_ticks(
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


def _sequence_belongs_to_dataset(session: Session, sequence_id: UUID, dataset_id: UUID) -> bool:
    """Whether `sequence_id` is an MCAP sequence whose collection is in `dataset_id`.

    Membership derives from the sequence sample's own collection, not from its
    recording: the two can differ, and a sequence has a valid collection even before
    its GROUP component schema exists.
    """
    if mcap_group_sequence_resolver.get_by_id(session=session, sample_id=sequence_id) is None:
        return False
    sample = sample_resolver.get_by_id(session=session, sample_id=sequence_id)
    if sample is None:
        return False
    collection = collection_resolver.get_by_id(session=session, collection_id=sample.collection_id)
    return collection is not None and collection.dataset_id == dataset_id
