import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.image import ImageView
from lightly_studio.models.video import VideoView
from lightly_studio.resolvers import collection_resolver, group_resolver
from tests.helpers_resolvers import ImageStub, create_collection, create_images
from tests.resolvers.video.helpers import VideoStub, create_video


def test_get_group_previews__no_collections(db_session: Session) -> None:
    """Test that empty list of group IDs returns empty dict."""
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    with pytest.raises(
        ValueError, match="No component collections found for the given group collection."
    ):
        group_resolver.get_group_previews(
            session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[]
        )


def test_get_group_previews__empty_list(db_session: Session) -> None:
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("component1", SampleType.IMAGE), ("component2", SampleType.IMAGE)],
    )
    result = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[]
    )
    assert result == {}


def test_get_group_previews__with_images(db_session: Session) -> None:
    """Test getting previews for groups containing images."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("component1", SampleType.IMAGE), ("component2", SampleType.IMAGE)],
    )

    # Create images - one for each component
    image1 = create_images(
        db_session=db_session,
        collection_id=components["component1"].collection_id,
        images=[ImageStub(path="image1.jpg")],
    )[0]
    image2 = create_images(
        db_session=db_session,
        collection_id=components["component2"].collection_id,
        images=[ImageStub(path="image2.jpg")],
    )[0]

    # Create a group with the images
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{image1.sample_id, image2.sample_id}],
    )[0]

    # Get previews
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[group_id]
    )

    # Should return the first image (by creation time)
    assert len(previews) == 1
    assert group_id in previews
    snapshot = previews[group_id]
    assert isinstance(snapshot, ImageView)
    assert snapshot.sample_id == image1.sample_id
    assert snapshot.file_name == "image1.jpg"


def test_get_group_previews__with_videos(db_session: Session) -> None:
    """Test getting previews for groups containing videos."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("component1", SampleType.VIDEO), ("component2", SampleType.VIDEO)],
    )

    # Create videos - one for each component
    video1 = create_video(
        session=db_session,
        collection_id=components["component1"].collection_id,
        video=VideoStub(path="/path/to/video1.mp4"),
    )
    video2 = create_video(
        session=db_session,
        collection_id=components["component2"].collection_id,
        video=VideoStub(path="/path/to/video2.mp4"),
    )

    # Create a group with the videos
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{video1.sample_id, video2.sample_id}],
    )[0]

    # Get previews
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[group_id]
    )

    # Should return the first video (by creation time)
    assert len(previews) == 1
    assert group_id in previews
    snapshot = previews[group_id]
    assert isinstance(snapshot, VideoView)
    assert snapshot.sample_id == video1.sample_id
    assert snapshot.file_name == "video1.mp4"


def test_get_group_previews__prefers_images_over_videos(db_session: Session) -> None:
    """Test that images are preferred over videos when both exist."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[
            ("image_component", SampleType.IMAGE),
            ("video_component", SampleType.VIDEO),
        ],
    )
    components = collection_resolver.get_group_components(
        session=db_session, parent_collection_id=group_col.collection_id
    )

    # Create a video first (so it has earlier creation time)
    video = create_video(
        session=db_session,
        collection_id=components["video_component"].collection_id,
        video=VideoStub(path="/path/to/video.mp4"),
    )

    # Create an image second
    image = create_images(
        db_session=db_session,
        collection_id=components["image_component"].collection_id,
        images=[ImageStub(path="image.jpg")],
    )[0]

    # Create a group with both
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{video.sample_id, image.sample_id}],
    )[0]

    # Get previews
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[group_id]
    )

    # Should return the image, not the video
    assert len(previews) == 1
    assert group_id in previews
    snapshot = previews[group_id]
    assert isinstance(snapshot, ImageView)
    assert snapshot.sample_id == image.sample_id


def test_get_group_previews__multiple_groups(db_session: Session) -> None:
    """Test getting previews for multiple groups at once."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    components = collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("component1", SampleType.IMAGE), ("component2", SampleType.IMAGE)],
    )

    # Create images - one for each component
    image1 = create_images(
        db_session=db_session,
        collection_id=components["component1"].collection_id,
        images=[ImageStub(path="image1.jpg")],
    )[0]
    image2 = create_images(
        db_session=db_session,
        collection_id=components["component2"].collection_id,
        images=[ImageStub(path="image2.jpg")],
    )[0]
    image3 = create_images(
        db_session=db_session,
        collection_id=components["component1"].collection_id,
        images=[ImageStub(path="image3.jpg")],
    )[0]

    # Create two groups
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{image1.sample_id}, {image2.sample_id, image3.sample_id}],
    )

    # Get previews for both groups
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=group_ids
    )

    # Should return snapshot for each group
    assert len(previews) == 2
    assert group_ids[0] in previews
    assert group_ids[1] in previews
    snapshot0 = previews[group_ids[0]]
    assert snapshot0 is not None
    assert snapshot0.sample_id == image1.sample_id
    # Should return image2 (alphabetically first by file_path_abs: "image2.jpg" < "image3.jpg")
    snapshot1 = previews[group_ids[1]]
    assert snapshot1 is not None
    assert snapshot1.sample_id == image3.sample_id


def test_get_group_previews__mixed_image_and_video_groups(db_session: Session) -> None:
    """Test getting previews for multiple groups with different sample types."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[
            ("front_image", SampleType.IMAGE),
            ("video_component", SampleType.VIDEO),
        ],
    )
    components = collection_resolver.get_group_components(
        session=db_session, parent_collection_id=group_col.collection_id
    )

    # Create an image
    image = create_images(
        db_session=db_session,
        collection_id=components["front_image"].collection_id,
        images=[ImageStub(path="image.jpg")],
    )[0]

    # Create a video
    video = create_video(
        session=db_session,
        collection_id=components["video_component"].collection_id,
        video=VideoStub(path="/path/to/video.mp4"),
    )

    # Create two groups: one with image, one with video
    group_ids = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[{image.sample_id}, {video.sample_id}],
    )

    # Get previews
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=group_ids
    )

    # We expect to get an image snapshot for the first group and None for the second group
    # because the first component is an image and the video group doesn't have an image sample.
    assert len(previews) == 2
    assert isinstance(previews[group_ids[0]], ImageView)
    # assert previews[group_ids[0]].sample_id == image.sample_id
    assert previews[group_ids[1]] is None


def test_get_group_previews__empty_group(db_session: Session) -> None:
    """Test that groups with no components return no snapshot."""
    # Create collections
    group_col = create_collection(session=db_session, sample_type=SampleType.GROUP)
    collection_resolver.create_group_components(
        session=db_session,
        parent_collection_id=group_col.collection_id,
        components=[("component", SampleType.IMAGE)],
    )

    # Create an empty group
    group_id = group_resolver.create_many(
        session=db_session,
        collection_id=group_col.collection_id,
        groups=[set()],
    )[0]

    # Get previews
    previews = group_resolver.get_group_previews(
        session=db_session, group_collection_id=group_col.collection_id, group_sample_ids=[group_id]
    )

    # Should return the group_id mapped to None as the group has no samples
    assert previews == {group_id: None}
