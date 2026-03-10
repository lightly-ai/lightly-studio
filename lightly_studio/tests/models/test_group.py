"""Tests for group models."""

from sqlmodel import Session

from lightly_studio.models.collection import ComponentCollectionView, SampleType
from lightly_studio.models.group import GroupComponentView
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_component_collection_view_from_collection_table(db_session: Session) -> None:
    """Test ComponentCollectionView.from_collection_table() factory method."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection.group_component_name = "front_camera"
    collection.group_component_index = 0
    db_session.add(collection)
    db_session.commit()

    result = ComponentCollectionView.from_collection_table(collection=collection)

    assert isinstance(result, ComponentCollectionView)
    assert result.name == collection.name
    assert result.parent_collection_id == collection.parent_collection_id
    assert result.sample_type == SampleType.VIDEO
    assert result.group_component_name == "front_camera"
    assert result.group_component_index == 0


def test_group_component_view_from_image_table(db_session: Session) -> None:
    """Test GroupComponentView.from_image_table() factory method."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection.group_component_name = "front_camera"
    collection.group_component_index = 0
    db_session.add(collection)
    db_session.commit()

    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="image.jpg")],
    )[0]

    component_collection = ComponentCollectionView(
        name=collection.name,
        parent_collection_id=collection.parent_collection_id,
        sample_type=collection.sample_type,
        group_component_name="front_camera",
        group_component_index=0,
    )

    result = GroupComponentView.from_image_table(image=image, collection=component_collection)

    assert isinstance(result, GroupComponentView)
    assert result.collection.group_component_name == "front_camera"
    assert result.collection.group_component_index == 0
    assert result.details is not None
    assert isinstance(result.details, ImageView)
    assert result.details.sample_id == image.sample_id
    assert result.details.file_name == "image.jpg"
    assert result.details.file_path_abs == image.file_path_abs
    assert result.details.width == image.width
    assert result.details.height == image.height
    assert result.details.sample.sample_id == image.sample_id


def test_group_component_view_from_video_table(db_session: Session) -> None:
    """Test GroupComponentView.from_video_table() factory method."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection.group_component_name = "rear_camera"
    collection.group_component_index = 1
    db_session.add(collection)
    db_session.commit()

    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video.mp4"),
    )

    component_collection = ComponentCollectionView(
        name=collection.name,
        parent_collection_id=collection.parent_collection_id,
        sample_type=collection.sample_type,
        group_component_name="rear_camera",
        group_component_index=1,
    )

    result = GroupComponentView.from_video_table(video=video, collection=component_collection)

    assert isinstance(result, GroupComponentView)
    assert result.collection.group_component_name == "rear_camera"
    assert result.collection.group_component_index == 1
    assert result.details is not None
    assert isinstance(result.details, VideoView)
    assert result.details.sample_id == video.sample_id
    assert result.details.file_name == "video.mp4"
    assert result.details.file_path_abs == video.file_path_abs
    assert result.details.width == video.width
    assert result.details.height == video.height
    assert result.details.fps == video.fps
    assert result.details.duration_s == video.duration_s
    assert result.details.sample.sample_id == video.sample_id
