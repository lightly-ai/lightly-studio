"""Tests for get_sample_details_by_id resolver."""

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.group import GroupView
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, group_resolver, sample_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_image, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_sample_details_by_id_image(db_session: Session) -> None:
    """Test getting sample details for an image sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    image = create_image(session=db_session, collection_id=collection.collection_id)

    result = sample_resolver.get_sample_details_by_id(session=db_session, sample_id=image.sample_id)

    assert isinstance(result, ImageView)
    assert result.sample_id == image.sample_id
    assert result.file_name == image.file_name


def test_get_sample_details_by_id_video(db_session: Session) -> None:
    """Test getting sample details for a video sample."""
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="test.mp4"),
    )

    result = sample_resolver.get_sample_details_by_id(session=db_session, sample_id=video.sample_id)

    assert isinstance(result, VideoView)
    assert result.sample_id == video.sample_id
    assert result.file_name == video.file_name


def test_get_sample_details_by_id_group(db_session: Session) -> None:
    """Test getting sample details for a group sample."""
    # Create group collection with components
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

    result = sample_resolver.get_sample_details_by_id(session=db_session, sample_id=group_id)

    assert isinstance(result, GroupView)
    assert result.sample_id == group_id


def test_get_sample_details_by_id_nonexistent(db_session: Session) -> None:
    """Test getting sample details for non-existent sample raises ValueError."""
    import uuid

    non_existent_id = uuid.uuid4()
    with pytest.raises(ValueError, match="does not exist"):
        sample_resolver.get_sample_details_by_id(session=db_session, sample_id=non_existent_id)


def test_get_sample_details_by_id_image_not_found(db_session: Session) -> None:
    """Test ValueError when image sample exists but image table entry doesn't."""
    from lightly_studio.models.sample import SampleCreate

    collection = create_collection(session=db_session, sample_type=SampleType.IMAGE)
    # Create sample without corresponding image entry
    sample = sample_resolver.create(
        session=db_session, sample=SampleCreate(collection_id=collection.collection_id)
    )

    with pytest.raises(ValueError, match="Image with sample_id .* not found"):
        sample_resolver.get_sample_details_by_id(session=db_session, sample_id=sample.sample_id)


def test_get_sample_details_by_id_video_not_found(db_session: Session) -> None:
    """Test ValueError when video sample exists but video table entry doesn't."""
    from lightly_studio.models.sample import SampleCreate

    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    # Create sample without corresponding video entry
    sample = sample_resolver.create(
        session=db_session, sample=SampleCreate(collection_id=collection.collection_id)
    )

    with pytest.raises(ValueError, match="Video with sample_id .* not found"):
        sample_resolver.get_sample_details_by_id(session=db_session, sample_id=sample.sample_id)


def test_get_sample_details_by_id_group_not_found(db_session: Session) -> None:
    """Test ValueError when group sample exists but group table entry doesn't."""
    from lightly_studio.models.sample import SampleCreate

    collection = create_collection(session=db_session, sample_type=SampleType.GROUP)
    # Create sample without corresponding group entry
    sample = sample_resolver.create(
        session=db_session, sample=SampleCreate(collection_id=collection.collection_id)
    )

    with pytest.raises(ValueError, match="Group with sample_id .* not found"):
        sample_resolver.get_sample_details_by_id(session=db_session, sample_id=sample.sample_id)
