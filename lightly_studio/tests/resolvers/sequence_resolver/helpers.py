"""Helpers for sequence resolver tests."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.recording import RecordingFormat
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import (
    mcap_group_sequence_resolver,
    recording_resolver,
    sample_resolver,
)
from tests.helpers_resolvers import create_collection


def create_sequence_and_samples(session: Session, sample_count: int) -> tuple[UUID, list[UUID]]:
    """Create a sequence and `sample_count` samples that can be added to it."""
    collection = create_collection(session=session, sample_type=SampleType.SEQUENCE)
    recording_id = recording_resolver.create(
        session=session,
        dataset_id=collection.dataset_id,
        uri="/bags/drive_001.mcap",
        format_=RecordingFormat.MCAP,
    )
    sequence_sample_id = mcap_group_sequence_resolver.create(
        session=session,
        collection_id=collection.collection_id,
        recording_id=recording_id,
    )
    group_collection = create_collection(
        session=session,
        sample_type=SampleType.GROUP,
        parent_collection_id=collection.collection_id,
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[
            SampleCreate(collection_id=group_collection.collection_id) for _ in range(sample_count)
        ],
    )
    return sequence_sample_id, sample_ids
