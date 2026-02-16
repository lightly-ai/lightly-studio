from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_collection,
)
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_filter_new_paths(test_db: Session) -> None:
    # 1. Case: empty DB, all paths are new
    collection = create_collection(session=test_db, sample_type=SampleType.VIDEO)

    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/video.mp4"],
    )

    assert file_paths_new == ["/path/to/video.mp4"]
    assert file_paths_old == []

    # Case 2: db non empty, same paths are new same are old
    create_videos(
        session=test_db,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )

    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/video.mp4", "/path/to/video_new.mp4"],
    )

    assert file_paths_new == ["/path/to/video_new.mp4"]
    assert file_paths_old == ["/path/to/video.mp4"]

    # Case 3: db non empty, only old
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=["/path/to/video.mp4"],
    )

    assert file_paths_new == []
    assert file_paths_old == ["/path/to/video.mp4"]

    # Case 4: db non empty, empty request
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection.collection_id,
        file_paths_abs=[],
    )

    assert file_paths_new == []
    assert file_paths_old == []


def test_filter_new_paths_same_path_different_collections(test_db: Session) -> None:
    """The same file_path_abs can be added to different collections independently."""
    collection_a = create_collection(
        session=test_db, collection_name="collection_a", sample_type=SampleType.VIDEO
    )
    collection_b = create_collection(
        session=test_db, collection_name="collection_b", sample_type=SampleType.VIDEO
    )

    # Add video to collection A
    create_videos(
        session=test_db,
        collection_id=collection_a.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )

    # The path should be "old" in collection A
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection_a.collection_id,
        file_paths_abs=["/path/to/video.mp4"],
    )
    assert file_paths_new == []
    assert file_paths_old == ["/path/to/video.mp4"]

    # The same path should be "new" in collection B
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db,
        collection_id=collection_b.collection_id,
        file_paths_abs=["/path/to/video.mp4"],
    )
    assert file_paths_new == ["/path/to/video.mp4"]
    assert file_paths_old == []
