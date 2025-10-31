from sqlmodel import Session

from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import (
    create_dataset,
)
from tests.resolvers.video_resolver.helpers import SampleVideo, create_video


def test_filter_new_paths(test_db: Session) -> None:
    # 1. Case: empty DB, all paths are new
    dataset = create_dataset(session=test_db)

    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/video.mp4"]
    )

    assert file_paths_new == ["/path/to/video.mp4"]
    assert file_paths_old == []

    # Case 2: db non empty, same paths are new same are old
    create_video(
        session=test_db,
        dataset_id=dataset.dataset_id,
        video=SampleVideo(file_path_abs="/path/to/video.mp4"),
    )

    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/video.mp4", "/path/to/video_new.mp4"]
    )

    assert file_paths_new == ["/path/to/video_new.mp4"]
    assert file_paths_old == ["/path/to/video.mp4"]

    # Case 2: db non empty, only old
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db, file_paths_abs=["/path/to/video.mp4"]
    )

    assert file_paths_new == []
    assert file_paths_old == ["/path/to/video.mp4"]

    # Case 3: db non empty, empty request
    file_paths_new, file_paths_old = video_resolver.filter_new_paths(
        session=test_db, file_paths_abs=[]
    )

    assert file_paths_new == []
    assert file_paths_old == []
