import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import mcap_resolver
from tests.helpers_resolvers import create_collection, create_mcap


def test_get_many_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
    collection_id = collection.collection_id
    mcap1 = create_mcap(session=db_session, collection_id=collection_id, channel_id=1)
    mcap2 = create_mcap(session=db_session, collection_id=collection_id, channel_id=2)

    samples = mcap_resolver.get_many_by_id(
        session=db_session, sample_ids=[mcap1.sample_id, mcap2.sample_id]
    )

    assert len(samples) == 2
    assert samples[0].channel_id == 1
    assert samples[1].channel_id == 2


def test_get_many_by_id__skips_missing(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.MCAP)
    mcap = create_mcap(session=db_session, collection_id=collection.collection_id)

    samples = mcap_resolver.get_many_by_id(
        session=db_session, sample_ids=[mcap.sample_id, uuid.uuid4()]
    )

    assert len(samples) == 1
    assert samples[0].sample_id == mcap.sample_id


def test_get_many_by_id__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More ids than PostgreSQL's 65,535-parameter cap.
    sample_ids = [uuid.uuid4() for _ in range(70_000)]
    assert mcap_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids) == []
