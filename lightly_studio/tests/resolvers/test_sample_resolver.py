from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_dataset


def test_create_and_get_by_id(db_session: Session) -> None:
    dataset = create_dataset(session=db_session)
    dataset_id = dataset.dataset_id

    create = SampleCreate(dataset_id=dataset_id)
    sample = sample_resolver.create(session=db_session, sample=create)
    assert sample.dataset_id == dataset_id

    fetched_sample = sample_resolver.get_by_id(session=db_session, sample_id=sample.sample_id)
    assert fetched_sample is not None
    assert fetched_sample.sample_id == sample.sample_id
    assert fetched_sample.dataset_id == dataset_id


def test_create_many_and_get_many_by_id(db_session: Session) -> None:
    dataset1 = create_dataset(session=db_session)
    dataset1_id = dataset1.dataset_id
    dataset2 = create_dataset(session=db_session, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    creates = [
        SampleCreate(dataset_id=dataset1_id),
        SampleCreate(dataset_id=dataset2_id),
        SampleCreate(dataset_id=dataset1_id),
    ]
    sample_ids = sample_resolver.create_many(session=db_session, samples=creates)
    assert len(sample_ids) == 3

    fetched_samples = sample_resolver.get_many_by_id(session=db_session, sample_ids=sample_ids)
    assert len(fetched_samples) == 3
    assert fetched_samples[0].sample_id == sample_ids[0]
    assert fetched_samples[0].dataset_id == dataset1_id
    assert fetched_samples[1].sample_id == sample_ids[1]
    assert fetched_samples[1].dataset_id == dataset2_id
    assert fetched_samples[2].sample_id == sample_ids[2]
    assert fetched_samples[2].dataset_id == dataset1_id


def test_count_by_dataset_id(db_session: Session) -> None:
    dataset1 = create_dataset(session=db_session)
    dataset1_id = dataset1.dataset_id
    dataset2 = create_dataset(session=db_session, dataset_name="dataset2")
    dataset2_id = dataset2.dataset_id

    creates = [
        SampleCreate(dataset_id=dataset1_id),
        SampleCreate(dataset_id=dataset2_id),
        SampleCreate(dataset_id=dataset1_id),
    ]
    sample_ids = sample_resolver.create_many(session=db_session, samples=creates)
    assert len(sample_ids) == 3
    assert sample_resolver.count_by_dataset_id(session=db_session, dataset_id=dataset1_id) == 2
    assert sample_resolver.count_by_dataset_id(session=db_session, dataset_id=dataset2_id) == 1
