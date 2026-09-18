"""Implementation of add_samples for sequences."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlmodel import Session, col, insert, select

from lightly_studio.models.sample import SampleTable
from lightly_studio.models.sequence import (
    SampleSequenceLinkCreate,
    SampleSequenceLinkTable,
    SequenceTable,
)
from lightly_studio.utils import batching


def add_samples(
    session: Session,
    sequence_sample_id: UUID,
    links: Sequence[SampleSequenceLinkCreate],
) -> None:
    """Put samples in the slots of a sequence, in a single commit.

    A sample sits in at most one slot of at most one sequence, and a slot holds at most
    one sample. A repeated ``sample_id`` or ``seq_number``, within ``links`` or against
    what the sequence already holds, violates those constraints and raises.

    Args:
        session: The database session.
        sequence_sample_id: The sample ID of the sequence, e.g. from
            ``mcap_group_sequence_resolver.create``.
        links: The samples to link and the slot of each. For an MCAP dataset the sample
            IDs are group sample IDs. Nothing is written for an empty sequence of links.

    Raises:
        ValueError: If the sequence or one of the samples does not exist, or if a
            ``seq_number`` is negative.
        sqlalchemy.exc.IntegrityError: If a sample is already in a sequence, or if a
            slot is taken.
    """
    if not links:
        return
    _check_links(session=session, sequence_sample_id=sequence_sample_id, links=links)

    rows = [
        {
            "sample_id": link.sample_id,
            "sequence_sample_id": sequence_sample_id,
            "seq_number": link.seq_number,
            "timestamp_ns": link.timestamp_ns,
        }
        for link in links
    ]
    for batch in batching.batched(items=rows):
        session.execute(insert(SampleSequenceLinkTable).values(batch))
    session.commit()


def _check_links(
    session: Session,
    sequence_sample_id: UUID,
    links: Sequence[SampleSequenceLinkCreate],
) -> None:
    """Check that the sequence and every sample exist, and that no slot is negative.

    Raises:
        ValueError: If a check fails.
    """
    for link in links:
        if link.seq_number < 0:
            raise ValueError(f"seq_number must not be negative, got {link.seq_number}.")
    if session.get(SequenceTable, sequence_sample_id) is None:
        raise ValueError(f"Sequence with sample_id {sequence_sample_id} not found.")
    _check_samples_exist(session=session, sample_ids=[link.sample_id for link in links])


def _check_samples_exist(session: Session, sample_ids: Sequence[UUID]) -> None:
    """Check that every sample ID has a sample row.

    Raises:
        ValueError: If a sample does not exist.
    """
    for batch in batching.batched(items=sample_ids):
        statement = select(SampleTable.sample_id).where(col(SampleTable.sample_id).in_(batch))
        found_ids = set(session.exec(statement).all())
        for sample_id in batch:
            if sample_id not in found_ids:
                raise ValueError(f"Sample with sample_id {sample_id} not found.")
