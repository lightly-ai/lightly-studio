"""Implementation of create for MCAP group sequences."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap_group_sequence import McapGroupSequenceTable
from lightly_studio.models.recording import RecordingTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sequence import SequenceTable
from lightly_studio.resolvers import collection_resolver, sample_resolver


def create(session: Session, collection_id: UUID, recording_id: UUID) -> UUID:
    """Create a sequence sample linked to an existing MCAP recording, in a single commit.

    Args:
        session: The database session.
        collection_id: The ID of the sequence collection.
        recording_id: The ID of the recording holding the MCAP bag path.

    Returns:
        The sample ID of the created sequence.

    Raises:
        ValueError: If the collection does not exist or is not of type SEQUENCE, or if
            the recording does not exist.
    """
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.SEQUENCE,
    )
    if session.get(RecordingTable, recording_id) is None:
        raise ValueError(f"Recording with id {recording_id} not found.")
    sample_id = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id)],
    )[0]
    session.bulk_save_objects(objects=[SequenceTable(sample_id=sample_id)])
    session.bulk_save_objects(
        objects=[McapGroupSequenceTable(sample_id=sample_id, recording_id=recording_id)]
    )
    session.commit()
    return sample_id
