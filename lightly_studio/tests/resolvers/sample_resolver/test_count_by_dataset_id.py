from sqlmodel import Session

from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import sample_resolver
from tests.helpers_resolvers import create_collection


def test_count_by_collection_id(db_session: Session) -> None:
    """Test counting samples by collection ID."""
    collection = create_collection(session=db_session)
    collection_id = collection.collection_id

    # Initially should be 0
    assert (
        sample_resolver.count_by_collection_id(session=db_session, collection_id=collection_id) == 0
    )

    # Create some samples
    creates = [
        SampleCreate(collection_id=collection_id),
        SampleCreate(collection_id=collection_id),
        SampleCreate(collection_id=collection_id),
    ]
    sample_resolver.create_many(session=db_session, samples=creates)

    # Should now count 3 samples
    assert (
        sample_resolver.count_by_collection_id(session=db_session, collection_id=collection_id) == 3
    )

    # Create another collection to ensure count is collection-specific
    collection2 = create_collection(session=db_session, collection_name="collection2")
    collection2_id = collection2.collection_id

    # Create some samples for the second collection
    creates = [
        SampleCreate(collection_id=collection2_id),
        SampleCreate(collection_id=collection2_id),
    ]
    sample_resolver.create_many(session=db_session, samples=creates)

    # Counts should be independent
    assert (
        sample_resolver.count_by_collection_id(session=db_session, collection_id=collection_id) == 3
    )
    assert (
        sample_resolver.count_by_collection_id(session=db_session, collection_id=collection2_id)
        == 2
    )
