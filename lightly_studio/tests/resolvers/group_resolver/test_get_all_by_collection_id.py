import pytest
from pydantic_core._pydantic_core import ValidationError
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver, tag_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_embedding_model,
    create_images,
    create_sample_embedding,
    create_tag,
)


def test_get_all_by_collection_id(db_session: Session) -> None:
    """Test basic retrieval of all groups."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg"), ImageStub(path="front_1.jpg")],
    )

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_images[0].sample_id}, {front_images[1].sample_id}],
    )

    # Act
    result = group_resolver.get_all_by_collection_id(
        session=db_session, collection_id=group_col.collection_id
    )

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    assert result.samples[0].sample_id == group_ids[0]
    assert result.samples[1].sample_id == group_ids[1]
    assert result.samples[0].sample.collection_id == group_col.collection_id


def test_get_all_by_collection_id__with_pagination(db_session: Session) -> None:
    """Test pagination of groups."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(5)],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Act - Get first 2 groups
    result_page_1 = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=2),
    )

    # Act - Get next 2 groups
    result_page_2 = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=2, limit=2),
    )

    # Act - Get remaining groups
    result_page_3 = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=4, limit=2),
    )

    # Assert - Check first page
    assert len(result_page_1.samples) == 2
    assert result_page_1.total_count == 5
    assert result_page_1.next_cursor == 2

    # Assert - Check second page
    assert len(result_page_2.samples) == 2
    assert result_page_2.total_count == 5
    assert result_page_2.next_cursor == 4

    # Assert - Check third page (should return 1 group)
    assert len(result_page_3.samples) == 1
    assert result_page_3.total_count == 5
    assert result_page_3.next_cursor is None

    # Assert - Check out of bounds (should return empty list)
    result_empty = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=5, limit=2),
    )
    assert len(result_empty.samples) == 0
    assert result_empty.total_count == 5


def test_get_all_by_collection_id__empty_output(db_session: Session) -> None:
    """Test retrieval when no groups exist."""
    # Create group collection without groups
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)

    # Act
    result = group_resolver.get_all_by_collection_id(
        session=db_session, collection_id=group_col.collection_id
    )

    # Assert
    assert len(result.samples) == 0
    assert result.total_count == 0


def test_get_all_by_collection_id__with_sample_ids(db_session: Session) -> None:
    """Test filtering by specific sample IDs."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(3)],
    )

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Select specific groups
    selected_ids = [group_ids[0], group_ids[2]]

    # Act
    result = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        sample_ids=selected_ids,
    )

    # Assert
    assert len(result.samples) == 2
    assert result.total_count == 2
    returned_ids = [group.sample_id for group in result.samples]
    assert all(group_id in returned_ids for group_id in selected_ids)


def test_get_all_by_collection_id__with_tag_filtering(db_session: Session) -> None:
    """Test filtering groups by tags."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create tags
    tag1 = create_tag(
        session=db_session,
        collection_id=group_col.collection_id,
        tag_name="tag_1",
        kind="sample",
    )
    tag2 = create_tag(
        session=db_session,
        collection_id=group_col.collection_id,
        tag_name="tag_2",
        kind="sample",
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(4)],
    )

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Add first 2 groups to tag1
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag1.tag_id,
        sample_ids=group_ids[:2],
    )

    # Add last 2 groups to tag2
    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag2.tag_id,
        sample_ids=group_ids[2:],
    )

    # Test filtering by tag1
    result_tag1 = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        filters=GroupFilter(sample_filter=SampleFilter(tag_ids=[tag1.tag_id])),
    )
    assert len(result_tag1.samples) == 2
    assert result_tag1.total_count == 2

    # Test filtering by tag2
    result_tag2 = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        filters=GroupFilter(sample_filter=SampleFilter(tag_ids=[tag2.tag_id])),
    )
    assert len(result_tag2.samples) == 2
    assert result_tag2.total_count == 2

    # Test filtering by both tags
    result_all = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        filters=GroupFilter(sample_filter=SampleFilter(tag_ids=[tag1.tag_id, tag2.tag_id])),
    )
    assert len(result_all.samples) == 4
    assert result_all.total_count == 4


def test_get_all_by_collection_id_with_embedding_sort(db_session: Session) -> None:
    """Test sorting groups by embedding similarity."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create embedding model
    embedding_model = create_embedding_model(
        session=db_session,
        collection_id=group_col.collection_id,
        embedding_model_name="example_embedding_model",
        embedding_dimension=3,
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(3)],
    )

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Create embeddings for groups
    create_sample_embedding(
        session=db_session,
        sample_id=group_ids[0],
        embedding=[1.0, 1.0, 1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=group_ids[1],
        embedding=[-1.0, -1.0, -1.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )
    create_sample_embedding(
        session=db_session,
        sample_id=group_ids[2],
        embedding=[1.0, 1.0, 2.0],
        embedding_model_id=embedding_model.embedding_model_id,
    )

    # Retrieve groups ordered by similarity to the provided embedding
    result = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        text_embedding=[-1.0, -1.0, -1.0],
    )

    # Assert
    assert len(result.samples) == 3
    assert result.total_count == 3
    assert result.samples[0].sample_id == group_ids[1]
    assert result.samples[1].sample_id == group_ids[2]
    assert result.samples[2].sample_id == group_ids[0]

    # Verify similarity scores are returned
    assert result.samples[0].similarity_score is not None
    assert result.samples[1].similarity_score is not None
    assert result.samples[2].similarity_score is not None
    assert result.samples[0].similarity_score == pytest.approx(1.0, abs=0.01)
    assert result.samples[0].similarity_score >= result.samples[1].similarity_score


def test_get_all_by_collection_id__returns_total_count(db_session: Session) -> None:
    """Test that total_count is correct with pagination."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(5)],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Test total count without pagination
    result = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=10),
    )
    assert len(result.samples) == 5
    assert result.total_count == 5

    # Test pagination with offset - total_count should remain the same
    result = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=2),
    )
    assert len(result.samples) == 2
    assert result.total_count == 5


def test_get_all_by_collection_id__limit(db_session: Session) -> None:
    """Test various limit scenarios."""
    # Create group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component samples
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(20)],
    )

    # Create groups
    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    # Retrieve all groups
    samples = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
    ).samples
    assert len(samples) == 20

    # Retrieve 10 groups
    samples = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=10),
    ).samples
    assert len(samples) == 10

    # Retrieve 1 group
    samples = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=1),
    ).samples
    assert len(samples) == 1

    # Retrieve 0 groups (should raise validation error)
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        group_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=group_col.collection_id,
            pagination=Paginated(offset=0, limit=0),
        )

    # Retrieve 100 groups (more than available)
    samples = group_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=group_col.collection_id,
        pagination=Paginated(offset=0, limit=100),
    ).samples
    assert len(samples) == 20

    # Retrieve -1 groups (should raise validation error)
    with pytest.raises(ValidationError, match="Input should be greater than 0"):
        group_resolver.get_all_by_collection_id(
            session=db_session,
            collection_id=group_col.collection_id,
            pagination=Paginated(offset=0, limit=-1),
        )
