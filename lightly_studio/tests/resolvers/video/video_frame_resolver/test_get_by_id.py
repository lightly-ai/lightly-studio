from sqlmodel import Session

from lightly_studio.models.dataset import SampleType
from lightly_studio.resolvers import video_frame_resolver
from tests.helpers_resolvers import create_dataset
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_get_by_id(test_db: Session) -> None:
    dataset = create_dataset(session=test_db, sample_type=SampleType.VIDEO)
    dataset_id = dataset.dataset_id

    video_frames = create_video_with_frames(
        session=test_db,
        dataset_id=dataset_id,
        video=VideoStub(path="/path/to/video1.mp4", duration_s=2.0, fps=1),
    )

    frame_sample_id = video_frames.frame_sample_ids[0]

    retrieved_frame = video_frame_resolver.get_by_id(
        session=test_db,
        sample_id=frame_sample_id,
    )

    assert retrieved_frame.sample_id == frame_sample_id
    assert retrieved_frame.video.duration_s == 2.0
    assert retrieved_frame.video.fps == 1.0
    assert retrieved_frame.video.file_path_abs == "/path/to/video1.mp4"
