"""Tests for get_group_component_details_by_group_id resolver."""

import uuid

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


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

    # Verify image components
    images = [r for r in results if isinstance(r.details, ImageView)]
    assert len(images) == 3
    front_result = next(r for r in images if r.collection.group_component_name == "front")
    assert isinstance(front_result.details, ImageView)
    assert front_result.details.file_name == "front.jpg"
    assert front_result.details.sample_id == front.sample_id
    assert front_result.details.file_path_abs == front.file_path_abs
    assert front_result.details.width == front.width
    assert front_result.details.height == front.height

    # Verify video components
    videos = [r for r in results if isinstance(r.details, VideoView)]
    assert len(videos) == 1
    camera_result = videos[0]
    assert camera_result.collection.group_component_name == "camera"
    assert isinstance(camera_result.details, VideoView)
    assert camera_result.details.file_name == "camera.mp4"
    assert camera_result.details.sample_id == camera.sample_id
    assert camera_result.details.file_path_abs == camera.file_path_abs
    assert camera_result.details.width == camera.width
    assert camera_result.details.height == camera.height
    assert camera_result.details.fps == camera.fps
    assert camera_result.details.duration_s == camera.duration_s


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
    non_existent_id = uuid.uuid4()
    results = group_resolver.get_group_component_details_by_group_id(
        session=db_session, group_id=non_existent_id
    )

    assert results == []
