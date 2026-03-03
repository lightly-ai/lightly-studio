"""Tests for group models."""

from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupComponentView
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_group_component_view_from_image_table(db_session: Session) -> None:
    """Test GroupComponentView.from_image_table() factory method."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    collection.group_component_name = "front_camera"
    db_session.add(collection)
    db_session.commit()

    image = create_images(
        db_session=db_session,
        collection_id=collection.collection_id,
        images=[ImageStub(path="image.jpg")],
    )[0]

    result = GroupComponentView.from_image_table(image=image, component_name="front_camera")

    assert isinstance(result, GroupComponentView)
    assert result.component_name == "front_camera"
    assert result.image is not None
    assert result.image.sample_id == image.sample_id
    assert result.image.file_name == "image.jpg"
    assert result.image.file_path_abs == image.file_path_abs
    assert result.image.width == image.width
    assert result.image.height == image.height
    assert result.image.sample.sample_id == image.sample_id
    assert result.video is None


def test_group_component_view_from_video_table(db_session: Session) -> None:
    """Test GroupComponentView.from_video_table() factory method."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    collection.group_component_name = "rear_camera"
    db_session.add(collection)
    db_session.commit()

    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="video.mp4"),
    )

    result = GroupComponentView.from_video_table(video=video, component_name="rear_camera")

    assert isinstance(result, GroupComponentView)
    assert result.component_name == "rear_camera"
    assert result.video is not None
    assert result.video.sample_id == video.sample_id
    assert result.video.file_name == "video.mp4"
    assert result.video.file_path_abs == video.file_path_abs
    assert result.video.width == video.width
    assert result.video.height == video.height
    assert result.video.fps == video.fps
    assert result.video.duration_s == video.duration_s
    assert result.video.sample.sample_id == video.sample_id
    assert result.image is None
