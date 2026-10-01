import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.mcap import McapCreate
from lightly_studio.resolvers import mcap_resolver
from tests.helpers_resolvers import create_collection


def test_create_many_samples(db_session: Session) -> None:
    """Test bulk creation of mcap samples, order preserved."""
    collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
    collection_id = collection.collection_id

    samples_to_create = [
        McapCreate(
            channel_id=3,
            log_time_ns=100,
            capture_timestamp_ns=100,
            keyframe_log_time_ns=90,
        ),
        McapCreate(
            channel_id=5,
            log_time_ns=200,
            capture_timestamp_ns=200,
        ),
    ]

    created_sample_ids = mcap_resolver.create_many(
        session=db_session, collection_id=collection_id, samples=samples_to_create
    )
    assert len(created_sample_ids) == 2

    retrieved_samples = mcap_resolver.get_many_by_id(
        session=db_session, sample_ids=created_sample_ids
    )

    # Order matches input order.
    assert len(retrieved_samples) == 2
    assert retrieved_samples[0].channel_id == 3
    assert retrieved_samples[0].keyframe_log_time_ns == 90
    assert retrieved_samples[0].sample.collection_id == collection_id

    assert retrieved_samples[1].channel_id == 5


def test_create_many__sample_type_mismatch(db_session: Session) -> None:
    """Creating mcap samples in a non-MCAP collection is rejected."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    with pytest.raises(ValueError, match="is having sample type 'image', expected 'mcap'"):
        mcap_resolver.create_many(
            session=db_session,
            collection_id=collection.collection_id,
            samples=[
                McapCreate(
                    channel_id=3,
                    log_time_ns=100,
                    capture_timestamp_ns=100,
                    keyframe_log_time_ns=90,
                ),
            ],
        )
