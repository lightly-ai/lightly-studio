"""Implementation of create functions for mcap locators."""

from __future__ import annotations

from uuid import UUID

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapCreate, McapTable
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import collection_resolver, sample_resolver


class McapCreateHelper(McapCreate):
    """Helper class to create McapTable with sample_id."""

    sample_id: UUID


def create_many(session: Session, collection_id: UUID, samples: list[McapCreate]) -> list[UUID]:
    """Create multiple mcap locator samples in a single database commit.

    Returns the list of created sample IDs that matches the order of input samples.
    """
    collection_resolver.check_collection_type(
        session=session,
        collection_id=collection_id,
        expected_type=SampleType.MCAP,
    )
    sample_ids = sample_resolver.create_many(
        session=session,
        samples=[SampleCreate(collection_id=collection_id) for _ in samples],
    )
    # Bulk create McapTable entries using the generated sample_ids.
    db_mcaps = [
        McapTable.model_validate(
            McapCreateHelper(
                channel_id=sample.channel_id,
                log_time_ns=sample.log_time_ns,
                capture_timestamp_ns=sample.capture_timestamp_ns,
                keyframe_log_time_ns=sample.keyframe_log_time_ns,
                sample_id=sample_id,
            )
        )
        for sample_id, sample in zip(sample_ids, samples)
    ]
    session.bulk_save_objects(db_mcaps)
    session.commit()
    return sample_ids
