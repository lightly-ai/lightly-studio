from sqlmodel import Session

from lightly_studio.resolvers import (
    video_frame_resolver,
)
from tests.resolvers.video_frame_resolver.helpers import create_fake_dataset_and_video_with_frames


def test_get_by_id(test_db: Session) -> None:
    dataset_id, frame_sample_id = create_fake_dataset_and_video_with_frames(test_db)

    retrieved_frame = video_frame_resolver.get_by_id(
        session=test_db,
        dataset_id=dataset_id,
        sample_id=frame_sample_id,
    )

    assert retrieved_frame.sample_id == frame_sample_id
