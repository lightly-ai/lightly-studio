from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection


def test_count_by_dataset_id(db_session: Session) -> None:
    """Test counting samples by dataset ID."""
    dataset = create_collection(session=db_session)
    dataset_id = dataset.collection_id

    # Initially should be 0
    assert sample_resolver.count_by_collection_id(session=db_session, collection_id=dataset_id) == 0

    # Create some samples
    creates = [
        SampleCreate(collection_id=dataset_id),
        SampleCreate(collection_id=dataset_id),
        SampleCreate(collection_id=dataset_id),
    ]
    sample_resolver.create_many(session=db_session, samples=creates)

    # Should now count 3 samples
    assert sample_resolver.count_by_collection_id(session=db_session, collection_id=dataset_id) == 3

    # Create another dataset to ensure count is dataset-specific
    dataset2 = create_collection(session=db_session, collection_name="dataset2")
    dataset2_id = dataset2.collection_id

    # Create some samples for the second dataset
    creates = [
        SampleCreate(collection_id=dataset2_id),
        SampleCreate(collection_id=dataset2_id),
    ]
    sample_resolver.create_many(session=db_session, samples=creates)

    # Counts should be independent
    assert sample_resolver.count_by_collection_id(session=db_session, collection_id=dataset_id) == 3
    assert (
        sample_resolver.count_by_collection_id(session=db_session, collection_id=dataset2_id) == 2
    )
