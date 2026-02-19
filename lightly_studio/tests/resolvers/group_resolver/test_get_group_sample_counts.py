import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, group_resolver
from lightly_studio.resolvers.group_resolver import get_group_sample_counts
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_group_sample_counts_empty_list(db_session: Session) -> None:
    """Test with empty group_sample_ids list."""
    with pytest.raises(ValueError, match="group_sample_ids cannot be empty"):
        get_group_sample_counts(session=db_session, group_sample_ids=[])


def test_get_group_sample_counts_single_group(db_session: Session) -> None:
    """Test counting samples in a single group."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]
    back_image = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_0.jpg")],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id, back_image.sample_id}],
    )[0]

    # Get sample counts
    result = get_group_sample_counts(session=db_session, group_sample_ids=[group_id])
    assert result == {group_id: 2}


def test_get_group_sample_counts_multiple_groups(db_session: Session) -> None:
    """Test counting samples in multiple groups."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create component samples for first group
    front_image_1 = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_1.jpg")],
    )[0]
    back_image_1 = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_1.jpg")],
    )[0]

    # Create component samples for second group
    front_image_2 = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_2.jpg")],
    )[0]
    back_image_2 = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back_2.jpg")],
    )[0]

    # Create component samples for third group (only one component)
    front_image_3 = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_3.jpg")],
    )[0]

    # Create groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[
            {front_image_1.sample_id, back_image_1.sample_id},
            {front_image_2.sample_id, back_image_2.sample_id},
            {front_image_3.sample_id},
        ],
    )

    # Get sample counts for all groups
    result = get_group_sample_counts(session=db_session, group_sample_ids=group_ids)
    assert result == {
        group_ids[0]: 2,
        group_ids[1]: 2,
        group_ids[2]: 1,
    }


def test_get_group_sample_counts_nonexistent_group(db_session: Session) -> None:
    """Test with a group ID that doesn't exist."""
    from uuid import uuid4

    nonexistent_id = uuid4()
    result = get_group_sample_counts(session=db_session, group_sample_ids=[nonexistent_id])
    assert result == {}
