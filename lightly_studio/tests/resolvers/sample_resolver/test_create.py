from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection


def test_create_and_get_by_id(db_session: Session) -> None:
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    create = SampleCreate(collection_id=collection_id)
    sample = sample_resolver.create(session=db_session, sample=create)
    assert sample.collection_id == collection_id

    fetched_sample = sample_resolver.get_by_id(session=db_session, sample_id=sample.sample_id)
    assert fetched_sample is not None
    assert fetched_sample.sample_id == sample.sample_id
    assert fetched_sample.collection_id == collection_id
