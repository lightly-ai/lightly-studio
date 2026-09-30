"""List the indexed recordings of one dataset."""

from __future__ import annotations

from typing import NamedTuple
from uuid import UUID

from sqlmodel import Session, col, select

from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.recording import RecordingTable


class RecordingSequence(NamedTuple):
    """One indexed recording and the sequence that holds its groups."""

    sample_id: UUID
    recording_id: UUID
    uri: str


def get_all_by_dataset_id(session: Session, dataset_id: UUID) -> list[RecordingSequence]:
    """Return each recording of the dataset together with its sequence."""
    rows = session.exec(
        select(
            McapGroupSequenceTable.sample_id,
            RecordingTable.recording_id,
            RecordingTable.uri,
        )
        .join(
            RecordingTable,
            col(McapGroupSequenceTable.recording_id) == col(RecordingTable.recording_id),
        )
        .where(col(RecordingTable.dataset_id) == dataset_id)
    ).all()
    return [
        RecordingSequence(sample_id=sample_id, recording_id=recording_id, uri=uri)
        for sample_id, recording_id, uri in rows
    ]
