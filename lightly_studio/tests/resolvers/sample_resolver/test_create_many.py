from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection


def test_create_many_and_get_many_by_id(db_session: Session) -> None:
    collection1 = create_collection(session=db_session)
    collection1_id = collection1.collection_id
    collection2 = create_collection(session=db_session, collection_name="collection2")
    collection2_id = collection2.collection_id

    creates = [
        SampleCreate(collection_id=collection1_id),
        SampleCreate(collection_id=collection2_id),
        SampleCreate(collection_id=collection1_id),
    ]
    sample_ids = sample_resolver.create_many(session=db_session, samples=creates)
    assert len(sample_ids) == 3

    fetched_samples = sample_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids)
    assert len(fetched_samples) == 3
    assert fetched_samples[0].sample_id == sample_ids[0]
    assert fetched_samples[0].collection_id == collection1_id
    assert fetched_samples[1].sample_id == sample_ids[1]
    assert fetched_samples[1].collection_id == collection2_id
    assert fetched_samples[2].sample_id == sample_ids[2]
    assert fetched_samples[2].collection_id == collection1_id


def test_create_many__empty(db_session: Session) -> None:
    assert sample_resolver.create_many(session=db_session, samples=[]) == []
