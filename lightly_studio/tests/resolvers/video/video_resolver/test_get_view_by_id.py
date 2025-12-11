from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import (
    video_resolver,
)
from tests.helpers_resolvers import create_dataset
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_get_view_by_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    create_videos(
        session=test_db,
        dataset_id=dataset_id,
        videos=[
            VideoStub(path="/path/to/sample1.mp4"),
            VideoStub(path="/path/to/sample2.mp4"),
        ],
    )

    videos = video_resolver.get_all_by_dataset_id(
        session=test_db,
        dataset_id=dataset_id,
    ).samples

    result = video_resolver.get_view_by_id(session=test_db, sample_id=videos[0].sample_id)

    assert result is not None
    assert result.file_name == "sample1.mp4"
