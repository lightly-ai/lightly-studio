"""Tests for get_group_component_details_by_group_id resolver."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupComponentView
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_group_component_details_by_group_id__single_image(db_session: Session) -> None:
    """Test getting group component details for a group with a single image component."""
    # Create parent group collection with image component
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("front", SampleType.IMAGE)],
    )

    # Create image in the component collection
    image = create_images(
        db_session=db_session,
        collection_id=components["front"].collection_id,
        images=[ImageStub(path="test.jpg")],
    )[0]

    # Create group linking the samples
    group_ids = group_resolver.create_many(
        session=db_session, collection_id=group_col.collection_id, groups=[{image.sample_id}]
    )

    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=group_ids[0]
    )

    assert len(results) == 1
    assert isinstance(results[0], GroupComponentView)
    assert results[0].collection.group_component_name == "front"
    assert isinstance(results[0].details, ImageView)
    assert results[0].details.sample_id == image.sample_id
    assert results[0].details.file_name == "test.jpg"
    assert results[0].details.file_path_abs == image.file_path_abs
    assert results[0].details.width == image.width
    assert results[0].details.height == image.height


def test_get_group_component_details_by_group_id__single_video(db_session: Session) -> None:
    """Test getting group component details for a group with a single video component."""
    # Create parent group collection with video component
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("camera", SampleType.VIDEO)],
    )

    # Create video in the component collection
    video = create_video(
        session=db_session,
        collection_id=components["camera"].collection_id,
        video=VideoStub(path="test.mp4"),
    )

    # Create group linking the samples
    group_ids = group_resolver.create_many(
        session=db_session, collection_id=group_col.collection_id, groups=[{video.sample_id}]
    )

    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=group_ids[0]
    )

    assert len(results) == 1
    assert isinstance(results[0], GroupComponentView)
    assert results[0].collection.group_component_name == "camera"
    assert isinstance(results[0].details, VideoView)
    assert results[0].details.sample_id == video.sample_id
    assert results[0].details.file_name == "test.mp4"
    assert results[0].details.file_path_abs == video.file_path_abs
    assert results[0].details.width == video.width
    assert results[0].details.height == video.height
    assert results[0].details.fps == video.fps
    assert results[0].details.duration_s == video.duration_s


def test_get_group_component_details_by_group_id__multiple_components(db_session: Session) -> None:
    """Test getting group component details for a group with multiple mixed components."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[
            ("front", SampleType.IMAGE),
            ("back", SampleType.IMAGE),
            ("side", SampleType.IMAGE),
            ("camera", SampleType.VIDEO),
        ],
    )

    # Create samples
    front = create_images(
        db_session, components["front"].collection_id, [ImageStub(path="front.jpg")]
    )[0]
    back = create_images(
        db_session, components["back"].collection_id, [ImageStub(path="back.jpg")]
    )[0]
    side = create_images(
        db_session, components["side"].collection_id, [ImageStub(path="side.jpg")]
    )[0]
    camera = create_video(
        db_session, components["camera"].collection_id, VideoStub(path="camera.mp4")
    )

    # Create group
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{front.sample_id, back.sample_id, side.sample_id, camera.sample_id}],
    )

    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=group_ids[0]
    )

    assert len(results) == 4
    assert {r.collection.group_component_name for r in results} == {
        "front",
        "back",
        "side",
        "camera",
    }

    images = [r for r in results if isinstance(r.details, ImageView)]
    videos = [r for r in results if isinstance(r.details, VideoView)]
    assert len(images) == 3
    assert len(videos) == 1


def test_get_group_component_details_by_group_id__empty_group(db_session: Session) -> None:
    """Test getting group component details for an empty group."""
    # Create parent group collection
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)

    # Create group with no samples
    group_ids = group_resolver.create_many(
        session=db_session, collection_id=group_col.collection_id, groups=[set()]
    )

    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=group_ids[0]
    )

    assert results == []


def test_get_group_component_details_by_group_id__nonexistent(db_session: Session) -> None:
    """Test getting group component details for non-existent group ID."""
    import uuid

    non_existent_id = uuid.uuid4()
    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=non_existent_id
    )

    assert results == []
