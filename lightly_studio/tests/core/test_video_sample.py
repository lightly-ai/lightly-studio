from sqlmodel import Session

from lightly_studio.core.video_sample import VideoSample
from lightly_studio.models.collection import SampleType
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


class TestImageSample:
    def test_video_sample(self, db_session: Session) -> None:
        dataset = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        dataset_id = dataset.collection_id

        video_table = create_video(
            session=db_session,
            collection_id=dataset_id,
            video=VideoStub(path="/path/to/sample1.mp4", width=320, height=240),
        )

        sample = VideoSample(inner=video_table)
        assert sample.file_name == "sample1.mp4"
        assert sample.width == 320
        assert sample.height == 240
        assert sample.dataset_id == dataset.collection_id
        assert sample.file_path_abs == "/path/to/sample1.mp4"
        assert sample.sample_id == video_table.sample_id
