from __future__ import annotations

import uuid

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.resolvers import collection_resolver


def test_get_or_create_child_collection(
    db_session: Session,
) -> None:
    """Test creating a video frame child collection."""
    # First tree
    video_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    # A new video frame child collection should be created.
    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )

    video_frames_collection = collection_resolver.get_by_id(
        session=db_session, collection_id=video_frames_collection_id
    )
    assert video_frames_collection is not None
    assert video_frames_collection.sample_type == SampleType.VIDEO_FRAME
    assert video_frames_collection.parent_collection_id == video_collection.collection_id
    assert video_frames_collection.name == "videos__video_frame"

    # Calling again should return the same collection ID.
    same_video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    assert same_video_frames_collection_id == video_frames_collection_id

    # No new collection should be created.
    collections = collection_resolver.get_hierarchy(
        session=db_session, dataset_id=video_collection.collection_id
    )
    assert len(collections) == 2
    assert collections[1].collection_id == video_frames_collection_id


def test_get_or_create_child_collection__existing_non_video_frame_collection_child(
    db_session: Session,
) -> None:
    """Test creating a video frame child collection."""
    # Create a video collection with a image child collection.
    video_collection = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="videos", sample_type=SampleType.VIDEO)
    )
    image_collection = collection_resolver.create(
        session=db_session,
        collection=CollectionCreate(
            name="images",
            sample_type=SampleType.IMAGE,
            parent_collection_id=video_collection.collection_id,
        ),
    )
    # A new video frame child collection should be created, because the child collection is of type
    # Image.
    video_frames_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session,
        collection_id=video_collection.collection_id,
        sample_type=SampleType.VIDEO_FRAME,
    )
    # Ensure that the new video frame child collection is different from the existing image
    # child collection.
    assert video_frames_collection_id != image_collection.collection_id

    # New child should be created even though there is already a child collection
    # with a different sample type.
    collections = collection_resolver.get_hierarchy(
        session=db_session, dataset_id=video_collection.collection_id
    )
    assert len(collections) == 3
    assert collections[1].collection_id == image_collection.collection_id
    assert collections[2].collection_id == video_frames_collection_id


def test_get_or_create_child_collection__non_existent(
    db_session: Session,
) -> None:
    non_existent_id = uuid.uuid4()
    with pytest.raises(ValueError, match=f"Collection with id {non_existent_id} not found"):
        collection_resolver.get_or_create_child_collection(
            session=db_session,
            collection_id=non_existent_id,
            sample_type=SampleType.CAPTION,
        )


def test_get_or_create_child_collection__return_direct_child(
    db_session: Session,
) -> None:
    collection_id = collection_resolver.create(
        session=db_session, collection=CollectionCreate(name="images", sample_type=SampleType.IMAGE)
    ).collection_id

    # Create a direct captions child collection
    child_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session, collection_id=collection_id, sample_type=SampleType.CAPTION
    )

    # Create a nested captions child collection
    grandchild_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session, collection_id=child_collection_id, sample_type=SampleType.CAPTION
    )
    assert child_collection_id != grandchild_collection_id

    # Fetching the captions child collection of the root collection should return the direct child
    fetched_child_collection_id = collection_resolver.get_or_create_child_collection(
        session=db_session, collection_id=collection_id, sample_type=SampleType.CAPTION
    )
    assert fetched_child_collection_id == child_collection_id
