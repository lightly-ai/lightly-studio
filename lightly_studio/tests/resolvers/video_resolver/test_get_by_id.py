from sqlmodel import Session

from lightly_studio.resolvers import (
    video_resolver,
)
from tests.conftest import create_videos_to_fake_dataset


def test_get_by_id(test_db: Session) -> None:
    videos = create_videos_to_fake_dataset(db_session=test_db)

    result = video_resolver.get_by_id(
        session=test_db, dataset_id=videos[0].sample.dataset_id, sample_id=videos[0].sample_id
    )

    assert result.file_name == "sample1.mp4"
