"""Tests for get_group_component_details_by_ids resolver."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupComponentView
from lightly_studio.resolvers import collection_resolver
from lightly_studio.resolvers.group_resolver.get_group_component_details_by_ids import (
    get_group_component_details_by_ids,
)
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_group_component_details_by_ids_single_image(db_session: Session) -> None:
    """Test getting group component details for a single image sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection.group_component_name = "front"
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)

    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="test.jpg")],
    )[0]

    results = get_group_component_details_by_ids(session=db_session, sample_ids=[image.sample_id])

    assert len(results) == 1
    assert isinstance(results[0], GroupComponentView)
    assert results[0].component_name == "front"
    assert results[0].image is not None
    assert results[0].image.sample_id == image.sample_id
    assert results[0].image.file_name == "test.jpg"
    assert results[0].image.file_path_abs == image.file_path_abs
    assert results[0].image.width == image.width
    assert results[0].image.height == image.height
    assert results[0].video is None


def test_get_group_component_details_by_ids_single_video(db_session: Session) -> None:
    """Test getting group component details for a single video sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection.group_component_name = "camera"
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)

    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="test.mp4"),
    )

    results = get_group_component_details_by_ids(session=db_session, sample_ids=[video.sample_id])

    assert len(results) == 1
    assert isinstance(results[0], GroupComponentView)
    assert results[0].component_name == "camera"
    assert results[0].video is not None
    assert results[0].video.sample_id == video.sample_id
    assert results[0].video.file_name == "test.mp4"
    assert results[0].video.file_path_abs == video.file_path_abs
    assert results[0].video.width == video.width
    assert results[0].video.height == video.height
    assert results[0].video.fps == video.fps
    assert results[0].video.duration_s == video.duration_s
    assert results[0].image is None


def test_get_group_component_details_by_ids_multiple_images(db_session: Session) -> None:
    """Test getting group component details for multiple image samples."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection.group_component_name = "front"
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)

    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"test_{i}.jpg") for i in range(3)],
    )

    sample_ids = [img.sample_id for img in images]
    results = get_group_component_details_by_ids(session=db_session, sample_ids=sample_ids)

    assert len(results) == 3
    for i, result in enumerate(results):
        assert result.component_name == "front"
        assert result.image is not None
        assert result.image.sample_id == images[i].sample_id
        assert result.video is None


def test_get_group_component_details_by_ids_mixed_types(db_session: Session) -> None:
    """Test getting group component details for mixed image and video samples."""
    image_collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image_collection.group_component_name = "front"
    db_session.add(image_collection)
    db_session.commit()
    db_session.refresh(image_collection)

    video_collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_collection.group_component_name = "camera"
    db_session.add(video_collection)
    db_session.commit()
    db_session.refresh(video_collection)

    image = create_images(
        db_session=db_session,
        collection_id=image_collection.collection_id,
        images=[ImageStub(path="test.jpg")],
    )[0]
    video = create_video(
        session=db_session,
        collection_id=video_collection.collection_id,
        video=VideoStub(path="test.mp4"),
    )

    results = get_group_component_details_by_ids(
        session=db_session, sample_ids=[image.sample_id, video.sample_id]
    )

    assert len(results) == 2
    # First result should be the image
    assert results[0].component_name == "front"
    assert results[0].image is not None
    assert results[0].image.sample_id == image.sample_id
    assert results[0].image.file_name == "test.jpg"
    assert results[0].image.width == image.width
    assert results[0].image.height == image.height
    assert results[0].video is None

    # Second result should be the video
    assert results[1].component_name == "camera"
    assert results[1].video is not None
    assert results[1].video.sample_id == video.sample_id
    assert results[1].video.file_name == "test.mp4"
    assert results[1].video.width == video.width
    assert results[1].video.height == video.height
    assert results[1].video.fps == video.fps
    assert results[1].image is None


def test_get_group_component_details_by_ids_empty_list(db_session: Session) -> None:
    """Test getting group component details with empty sample_ids list."""
    results = get_group_component_details_by_ids(session=db_session, sample_ids=[])

    assert results == []


def test_get_group_component_details_by_ids_nonexistent(db_session: Session) -> None:
    """Test getting group component details for non-existent sample IDs."""
    import uuid

    non_existent_ids = [uuid.uuid4(), uuid.uuid4()]
    results = get_group_component_details_by_ids(session=db_session, sample_ids=non_existent_ids)

    assert results == []


def test_get_group_component_details_by_ids_preserves_order(db_session: Session) -> None:
    """Test that results are returned in the same order as input sample_ids."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection.group_component_name = "front"
    db_session.add(collection)
    db_session.commit()
    db_session.refresh(collection)

    images = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path=f"test_{i}.jpg") for i in range(5)],
    )

    # Request in reverse order
    sample_ids = [img.sample_id for img in reversed(images)]
    results = get_group_component_details_by_ids(session=db_session, sample_ids=sample_ids)

    assert len(results) == 5
    for i, result in enumerate(results):
        assert result.image is not None
        assert result.image.sample_id == sample_ids[i]


def test_get_group_component_details_by_ids_no_component_name(db_session: Session) -> None:
    """Test getting group component details when collection has no group_component_name."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    # Don't set group_component_name, it should default to None

    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="test.jpg")],
    )[0]

    results = get_group_component_details_by_ids(session=db_session, sample_ids=[image.sample_id])

    assert len(results) == 1
    assert results[0].component_name == ""
    assert results[0].image is not None


def test_get_group_component_details_by_ids_multiple_collections(db_session: Session) -> None:
    """Test getting group component details for samples from different collections."""
    # Create parent group collection with multiple components
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE), ("back", SampleType.IMAGE)],
    )

    # Create samples in different component collections
    front_image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="front.jpg")],
    )[0]
    back_image = create_images(
        db_session=db_session,
        collection_id=components["back"].collection_id,
        images=[ImageStub(path="back.jpg")],
    )[0]

    results = get_group_component_details_by_ids(
        session=db_session, sample_ids=[front_image.sample_id, back_image.sample_id]
    )

    assert len(results) == 2
    assert results[0].component_name == "front"
    assert results[0].image is not None
    assert results[0].image.sample_id == front_image.sample_id
    assert results[0].image.file_name == "front.jpg"

    assert results[1].component_name == "back"
    assert results[1].image is not None
    assert results[1].image.sample_id == back_image.sample_id
    assert results[1].image.file_name == "back.jpg"
