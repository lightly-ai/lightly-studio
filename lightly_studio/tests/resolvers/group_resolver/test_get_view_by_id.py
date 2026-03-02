"""Tests for group_resolver.get_view_by_id."""

from uuid import uuid4

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupView
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images


def test_get_view_by_id_basic(db_session: Session) -> None:
    """Test getting view for a group."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create component sample
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]

    # Create a group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Call get_view_by_id
    result = group_resolver.get_view_by_id(session=db_session, sample_id=group_id)

    # Verify results
    assert isinstance(result, GroupView)
    assert result.sample_id == group_id
    assert result.sample.sample_id == group_id
    assert result.sample.collection_id == group_col.collection_id
    assert result.sample_count == 1
    assert result.similarity_score is None


def test_get_view_by_id_with_multiple_components(db_session: Session) -> None:
    """Test getting view for a group with multiple components."""
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

    # Call get_view_by_id
    result = group_resolver.get_view_by_id(session=db_session, sample_id=group_id)

    # Verify results
    assert isinstance(result, GroupView)
    assert result.sample_id == group_id
    assert result.sample_count == 2
    assert result.group_preview is not None


def test_get_view_by_id_non_existent_group(db_session: Session) -> None:
    """Test getting view for a non-existent group raises ValueError."""
    non_existent_id = uuid4()

    with pytest.raises(ValueError, match=f"Group with sample_id '{non_existent_id}' not found"):
        group_resolver.get_view_by_id(session=db_session, sample_id=non_existent_id)


def test_get_view_by_id_partial_group(db_session: Session) -> None:
    """Test getting view for a partial group (not all components present)."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create only front component sample (partial group)
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front_0.jpg")],
    )[0]

    # Create a partial group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front_image.sample_id}],
    )[0]

    # Call get_view_by_id
    result = group_resolver.get_view_by_id(session=db_session, sample_id=group_id)

    # Verify results - sample_count should be 1 (only front component)
    assert isinstance(result, GroupView)
    assert result.sample_id == group_id
    assert result.sample_count == 1
    assert result.group_preview is not None
