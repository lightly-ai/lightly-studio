from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_dataset


def test_create_and_get_by_id(db_session: Session) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.collection_id

    create = SampleCreate(collection_id=dataset_id)
    sample = sample_resolver.create(session=db_session, sample=create)
    assert sample.collection_id == dataset_id

    fetched_sample = sample_resolver.get_by_id(session=db_session, sample_id=sample.sample_id)
    assert fetched_sample is not None
    assert fetched_sample.sample_id == sample.sample_id
    assert fetched_sample.collection_id == dataset_id
