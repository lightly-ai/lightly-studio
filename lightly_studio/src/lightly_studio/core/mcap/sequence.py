"""An ordered sequence of the groups indexed from one recording."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.sequence import SampleSequenceLinkCreate
from lightly_studio.resolvers import sequence_resolver


@dataclass(frozen=True)
class McapSequenceEntry:
    """One slot of a sequence: which group sits in it, and when it was captured."""

    sample_id: UUID
    """The ID of the group sample in the slot."""
    seq_number: int
    """The position of the group in the sequence, counted from 0."""
    timestamp_ns: int | None = None
    """The time the data of the group was captured at, in nanoseconds.

    Usually the time of the component the others were synchronized against.
    """


class McapSequence:
    """The groups of one recording, in the order they were recorded in.

    The groups are added after they are created, in one call, so that the whole order
    of a recording is written in a single transaction:

    ```python
    sequence = dataset.create_sequence(recording_id=recording.recording_id)
    group_samples = [
        group_dataset.add_group_sample(components={...}) for sweep in sweeps
    ]
    sequence.add_samples(
        entries=[
            McapSequenceEntry(
                sample_id=group_sample.sample_id,
                seq_number=index,
                timestamp_ns=sweep.log_time_ns,
            )
            for index, (group_sample, sweep) in enumerate(zip(group_samples, sweeps))
        ]
    )
    ```
    """

    def __init__(self, session: Session, sample_id: UUID, recording_id: UUID) -> None:
        """Initialize the sequence.

        Args:
            session: Database session for resolver operations.
            sample_id: The ID of the sequence sample.
            recording_id: The ID of the recording the sequence was indexed from.
        """
        self._session = session
        self._sample_id = sample_id
        self._recording_id = recording_id

    @property
    def sample_id(self) -> UUID:
        """The ID of the sequence sample."""
        return self._sample_id

    @property
    def recording_id(self) -> UUID:
        """The ID of the recording the sequence was indexed from."""
        return self._recording_id

    def add_samples(self, entries: Sequence[McapSequenceEntry]) -> None:
        """Put groups in the slots of the sequence, in a single commit.

        A group sits in at most one slot of at most one sequence, and a slot holds at
        most one group. Nothing is written for an empty sequence of entries.

        Args:
            entries: The groups to add and the slot of each.

        Raises:
            ValueError: If a group does not exist, or if a `seq_number` is negative.
            sqlalchemy.exc.IntegrityError: If a group is already in a sequence, or if a
                slot is taken.
        """
        sequence_resolver.add_samples(
            session=self._session,
            sequence_sample_id=self._sample_id,
            links=[
                SampleSequenceLinkCreate(
                    sample_id=entry.sample_id,
                    seq_number=entry.seq_number,
                    timestamp_ns=entry.timestamp_ns,
                )
                for entry in entries
            ],
        )

    def get_samples(self) -> list[McapSequenceEntry]:
        """Get the groups of the sequence, in the order they were recorded in.

        Returns:
            One entry per slot of the sequence, ordered by `seq_number`.
        """
        links = sequence_resolver.get_sample_links(
            session=self._session, sequence_sample_id=self._sample_id
        )
        return [
            McapSequenceEntry(
                sample_id=link.sample_id,
                seq_number=link.seq_number,
                timestamp_ns=link.timestamp_ns,
            )
            for link in links
        ]
