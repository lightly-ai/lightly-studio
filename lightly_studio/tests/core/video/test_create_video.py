from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.core.video.create_video import CreateVideo
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import create_video_file


class TestCreateVideo:
    def test_create_in_collection(self, db_session: Session, tmp_path: Path) -> None:
        # Create a test Video file.
        create_video_file(
            output_path=tmp_path / "test_video.mp4",
            width=100,
            height=100,
            num_frames=30,
            fps=30,
        )

        # Create a video sample.
        ds = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        creator = CreateVideo(path=str(tmp_path / "test_video.mp4"))
        sample_id = creator.create_in_collection(session=db_session, collection_id=ds.collection_id)

        # Verify the video sample was created correctly.
        result = video_resolver.get_all_by_collection_id(
            session=db_session, collection_id=ds.collection_id
        )
        assert result.total_count == 1

        sample = result.samples[0]
        assert sample.sample_id == sample_id
        assert sample.file_name == "test_video.mp4"
        assert sample.width == 100
        assert sample.height == 100
        assert sample.fps == 30
        assert sample.duration_s == pytest.approx(1.0)

    def test_sample_type(self) -> None:
        creator = CreateVideo(path="dummy_path.jpg")
        assert creator.sample_type() == SampleType.VIDEO
