from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_child_collection_by_name(
    db_session: Session,
) -> None:
    """Test getting a child collection by name."""
    video_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )

    # Not found initially
    assert (
        collection_resolver.get_child_collection_by_name(
            session=db_session,
            collection_id=video_collection.collection_id,
            sample_type=SampleType.VIDEO_FRAME,
        )
        is None
    )

    # Create it
    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    # Now it should be found
    found_id = collection_resolver.get_child_collection_by_name(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    assert found_id == video_frames_collection_id


def test_get_child_collection_by_name__custom_name(
    db_session: Session,
) -> None:
    """Test getting a child collection with a custom name."""
    video_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )

    custom_name = "my_custom_frames"
    # Not found initially
    assert (
        collection_resolver.get_child_collection_by_name(
            session=db_session,
            collection_id=video_collection.collection_id,
            sample_type=SampleType.VIDEO_FRAME,
            name=custom_name,
        )
        is None
    )

    # Create it
    video_frames_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name=custom_name,
            sample_type=SampleType.VIDEO_FRAME,
            parent_collection_id=video_collection.collection_id,
        ),
    )

    # Now it should be found
    found_id = collection_resolver.get_child_collection_by_name(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
        name=custom_name,
    )
    assert found_id == video_frames_collection.collection_id


def test_get_child_collection_by_name__non_existent_parent(
    db_session: Session,
) -> None:
    non_existent_id = uuid.uuid4()
    with pytest.raises(ValueError, match=f"Collection with id {non_existent_id} not found"):
        collection_resolver.get_child_collection_by_name(
            session=db_session,
            collection_id=non_existent_id,
            sample_type=SampleType.CAPTION,
        )
