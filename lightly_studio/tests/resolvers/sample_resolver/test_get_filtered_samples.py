from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.resolvers import (
    sample_resolver,
    tag_resolver,
)
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_images,
    create_tag,
)


def test_get_filtered_samples__all(test_db: Session) -> None:
    # Create samples
    collection = create_collection(session=test_db)
    samples = create_images(
        db_session=test_db,
        collection_id=collection.collection_id,
        images=[ImageStub(path="s1.png"), ImageStub(path="s2.png")],
    )

    # Act
    result = sample_resolver.get_filtered_samples(session=test_db)

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert {result.samples[0].sample_id, result.samples[1].sample_id} == {
        samples[0].sample_id,
        samples[1].sample_id,
    }


def test_get_filtered_samples__empty_db(
    test_db: Session,
) -> None:
    # Act
    result = sample_resolver.get_filtered_samples(session=test_db)

    # Assert
    assert len(result.samples) == 0
    assert result.total_count == 0


def test_get_filtered_samples__default_order(
    test_db: Session,
) -> None:
    # Create samples
    collection = create_collection(session=test_db)
    samples = create_images(
        db_session=test_db,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="s1.png"),
            ImageStub(path="s2.png"),
            ImageStub(path="s3.png"),
            ImageStub(path="s4.png"),
            ImageStub(path="s5.png"),
        ],
    )

    # Sort samples by (created_at, sample_id) to match the expected order
    samples.sort(key=lambda x: (x.created_at, x.sample_id))

    # Act
    result = sample_resolver.get_filtered_samples(session=test_db)

    # Assert - Check first page
    assert len(result.samples) == 5
    assert result.total_count == 5
    assert result.samples[0].sample_id == samples[0].sample_id
    assert result.samples[1].sample_id == samples[1].sample_id
    assert result.samples[2].sample_id == samples[2].sample_id
    assert result.samples[3].sample_id == samples[3].sample_id
    assert result.samples[4].sample_id == samples[4].sample_id


def test_get_filtered_samples__pagination(
    test_db: Session,
) -> None:
    # Create samples
    collection = create_collection(session=test_db)
    samples = create_images(
        db_session=test_db,
        collection_id=collection.collection_id,
        images=[
            ImageStub(path="s1.png"),
            ImageStub(path="s2.png"),
            ImageStub(path="s3.png"),
            ImageStub(path="s4.png"),
            ImageStub(path="s5.png"),
        ],
    )

    # Sort samples by (created_at, sample_id) to match the expected order
    samples.sort(key=lambda x: (x.created_at, x.sample_id))

    # Act - Get first 2 samples
    result_page_1 = sample_resolver.get_filtered_samples(
        session=test_db, pagination=Paginated(offset=0, limit=2)
    )
    # Act - Get next 2 samples
    result_page_2 = sample_resolver.get_filtered_samples(
        session=test_db, pagination=Paginated(offset=2, limit=2)
    )
    # Act - Get remaining samples
    result_page_3 = sample_resolver.get_filtered_samples(
        session=test_db, pagination=Paginated(offset=4, limit=2)
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.samples[0].sample_id == samples[0].sample_id
    assert result_page_1.samples[1].sample_id == samples[1].sample_id

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.samples[0].sample_id == samples[2].sample_id
    assert result_page_2.samples[1].sample_id == samples[3].sample_id

    # Assert - Check third page (should return 1 sample)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.samples[0].sample_id == samples[4].sample_id

    # Assert - Check out of bounds (should return empty list)
    result_empty = sample_resolver.get_filtered_samples(
        session=test_db, pagination=Paginated(offset=5, limit=2)
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_filtered_samples__filters(
    test_db: Session,
) -> None:
    # Create samples
    collection = create_collection(session=test_db)
    collection_id = collection.collection_id
    samples = create_images(
        db_session=test_db,
        collection_id=collection_id,
        images=[
            ImageStub(path="sample1.png"),
            ImageStub(path="sample2.png"),
            ImageStub(path="sample3.png"),
        ],
    )

    # Add a tag to sample2
    tag = create_tag(session=test_db, collection_id=collection_id, tag_name="tag1", kind="sample")
    tag_resolver.add_sample_ids_to_tag_id(
        session=test_db,
        tag_id=tag.tag_id,
        sample_ids=[samples[1].sample_id],
    )

    # Test a few filter scenarios

    # By sample IDs
    result = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(sample_ids=[samples[0].sample_id, samples[2].sample_id]),
    )
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert {result.samples[0].sample_id, result.samples[1].sample_id} == {
        samples[0].sample_id,
        samples[2].sample_id,
    }

    # By tag and collection ID
    result = sample_resolver.get_filtered_samples(
        session=test_db,
        filters=SampleFilter(collection_id=collection_id, tag_ids=[tag.tag_id]),
    )
    assert len(result.samples) == 1
    assert result.total_count == 1
    assert result.samples[0].sample_id == samples[1].sample_id
