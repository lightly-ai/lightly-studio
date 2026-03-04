"""Tests for get_all function."""

import pytest
from sqlmodel import Session

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver, tag_resolver
from lightly_studio.resolvers.group_resolver.group_filter import GroupFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests.helpers_resolvers import (
    ImageStub,
    create_collection,
    create_images,
    create_tag,
)


def test_get_all__basic(db_session: Session) -> None:
    """Test basic retrieval without similarity."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg"), ImageStub(path="front_1.jpg")],
    )

    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_images[0].sample_id}, {front_images[1].sample_id}],
    )

    result = group_resolver.get_all(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 2
    assert result.total_count == 2
    returned_ids = [s.sample_id for s in result.samples]
    assert set(returned_ids) == set(group_ids)
    assert all(s.similarity_score is None for s in result.samples)
    # Verify group_preview is populated
    assert all(s.group_preview is not None for s in result.samples)
    assert all(
        s.group_preview.type == "image" for s in result.samples if s.group_preview is not None
    )
    # Verify image details
    first_sample_paths = {
        s.group_preview.file_path_abs for s in result.samples if s.group_preview is not None
    }
    expected_paths = {img.file_path_abs for img in front_images}
    assert first_sample_paths == expected_paths


def test_get_all__with_pagination(db_session: Session) -> None:
    """Test pagination without similarity."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(5)],
    )

    group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    result = group_resolver.get_all(
        session=db_session,
        pagination=Paginated(offset=0, limit=2),
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 2
    assert result.total_count == 5
    assert result.next_cursor == 2
    assert all(s.group_preview is not None for s in result.samples)
    assert all(
        s.group_preview.type == "image" for s in result.samples if s.group_preview is not None
    )


def test_get_all__with_filters(db_session: Session) -> None:
    """Test filtering without similarity."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    tag = create_tag(
        session=db_session,
        collection_id=group_col.collection_id,
        tag_name="test_tag",
        kind="sample",
    )

    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(3)],
    )

    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    tag_resolver.add_sample_ids_to_tag_id(
        session=db_session,
        tag_id=tag.tag_id,
        sample_ids=group_ids[:2],
    )

    result = group_resolver.get_all(
        session=db_session,
        pagination=None,
        filters=GroupFilter(
            sample_filter=SampleFilter(collection_id=group_col.collection_id, tag_ids=[tag.tag_id])
        ),
    )

    assert len(result.samples) == 2
    assert result.total_count == 2
    assert all(s.group_preview is not None for s in result.samples)
    assert all(
        s.group_preview.type == "image" for s in result.samples if s.group_preview is not None
    )


def test_get_all__empty(db_session: Session) -> None:
    """Test empty results without similarity."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)

    result = group_resolver.get_all(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert result.samples == []
    assert result.total_count == 0
    assert result.next_cursor is None


def test_get_all__without_collection_id(db_session: Session) -> None:
    """Test that request without collection_id raises an error."""
    with pytest.raises(
        ValueError, match="Collection ID must be provided in filters to fetch groups."
    ):
        group_resolver.get_all(
            session=db_session,
            pagination=None,
            filters=GroupFilter(sample_filter=SampleFilter()),
        )


def test_get_all__sample_counts(db_session: Session) -> None:
    """Test that sample_count is correctly populated for each group."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[
            ("front", SampleType.IMAGE),
            ("side", SampleType.IMAGE),
            ("back", SampleType.IMAGE),
        ],
    )

    # Create images for different components
    front_images = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path=f"front_{i}.jpg") for i in range(3)],
    )
    side_images = create_images(
        db_session=db_session,
        collection_id=components["side"].collection_id,
        images=[ImageStub(path=f"side_{i}.jpg") for i in range(3)],
    )
    back_images = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path=f"back_{i}.jpg") for i in range(3)],
    )

    # Create groups with different numbers of samples from different components:
    # Group 1: 3 samples (front, side, back)
    # Group 2: 2 samples (front, side)
    # Group 3: 1 sample (front)
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_images[0].sample_id, side_images[0].sample_id, back_images[0].sample_id},
            {front_images[1].sample_id, side_images[1].sample_id},
            {front_images[2].sample_id},
        ],
    )

    result = group_resolver.get_all(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 3
    assert result.total_count == 3

    # Verify sample counts match expected values
    sample_counts_by_id = {s.sample_id: s.sample_count for s in result.samples}
    assert sample_counts_by_id[group_ids[0]] == 3
    assert sample_counts_by_id[group_ids[1]] == 2
    assert sample_counts_by_id[group_ids[2]] == 1
