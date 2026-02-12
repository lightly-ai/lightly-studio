"""Tests for get_all_groups function."""

import time

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


def test_get_all_groups__basic(db_session: Session) -> None:
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

    result = group_resolver.get_all_groups(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 2
    assert result.total_count == 2
    returned_ids = [s.sample_id for s in result.samples]
    assert set(returned_ids) == set(group_ids)
    assert all(s.similarity_score is None for s in result.samples)


def test_get_all_groups__with_pagination(db_session: Session) -> None:
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

    result = group_resolver.get_all_groups(
        session=db_session,
        pagination=Paginated(offset=0, limit=2),
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 2
    assert result.total_count == 5
    assert result.next_cursor == 2


def test_get_all_groups__with_filters(db_session: Session) -> None:
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

    result = group_resolver.get_all_groups(
        session=db_session,
        pagination=None,
        filters=GroupFilter(
            sample_filter=SampleFilter(collection_id=group_col.collection_id, tag_ids=[tag.tag_id])
        ),
    )

    assert len(result.samples) == 2
    assert result.total_count == 2


def test_get_all_groups__empty(db_session: Session) -> None:
    """Test empty results without similarity."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)

    result = group_resolver.get_all_groups(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 0
    assert result.total_count == 0


def test_get_all_groups__ordered_by_created_at(db_session: Session) -> None:
    """Test that groups are ordered by sample created_at timestamp."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create images with explicit delays to ensure different created_at timestamps
    front_images = []
    for i in range(3):
        images = create_images(
            db_session=db_session,
            collection_id=components["front"].collection_id,
            images=[ImageStub(path=f"front_{i}.jpg")],
        )
        front_images.extend(images)
        time.sleep(0.01)  # Small delay to ensure different timestamps

    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{img.sample_id} for img in front_images],
    )

    result = group_resolver.get_all_groups(
        session=db_session,
        pagination=None,
        filters=GroupFilter(sample_filter=SampleFilter(collection_id=group_col.collection_id)),
    )

    assert len(result.samples) == 3
    # Verify order matches creation order
    returned_ids = [s.sample_id for s in result.samples]
    assert returned_ids == group_ids
