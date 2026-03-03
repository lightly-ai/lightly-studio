from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.models.video import VideoView
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video, create_video_with_frames


class TestVideoView:
    def test_from_video_table__basic(self, db_session: Session) -> None:
        """Test VideoView.from_video_table conversion function."""
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        collection_id = collection.collection_id

        video_table = create_video(
            session=db_session,
            collection_id=collection_id,
            video=VideoStub(
                path="/path/to/sample_video.mp4",
                width=1920,
                height=1080,
                duration_s=45.5,
                fps=24.0,
            ),
        )

        video_view = VideoView.from_video_table(video=video_table)

        assert video_view.type == SampleType.VIDEO
        assert video_view.width == 1920
        assert video_view.height == 1080
        assert video_view.duration_s == 45.5
        assert video_view.fps == 24.0
        assert video_view.file_name == "sample_video.mp4"
        assert video_view.file_path_abs == "/path/to/sample_video.mp4"
        assert video_view.sample_id == video_table.sample_id
        assert video_view.sample.sample_id == video_table.sample_id
        assert video_view.frame is None
        assert video_view.similarity_score is None

    def test_from_video_table__with_optional_params(self, db_session: Session) -> None:
        """Test VideoView.from_video_table with frame and similarity_score."""
        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        collection_id = collection.collection_id

        video_table = create_video(
            session=db_session,
            collection_id=collection_id,
            video=VideoStub(path="/path/to/test.mp4", width=640, height=480),
        )

        similarity_score = 0.95
        video_view = VideoView.from_video_table(
            video=video_table, frame=None, similarity_score=similarity_score
        )

        assert video_view.similarity_score == 0.95
        assert video_view.frame is None

    def test_from_video_table__with_frame(self, db_session: Session) -> None:
        """Test VideoView.from_video_table with VideoFrameTable conversion."""
        from lightly_studio.resolvers import video_frame_resolver

        collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
        collection_id = collection.collection_id

        video_with_frames = create_video_with_frames(
            session=db_session,
            collection_id=collection_id,
            video=VideoStub(
                path="/path/to/test.mp4",
                width=640,
                height=480,
                duration_s=10.0,
                fps=30.0,
            ),
        )

        # Get the video and first frame
        from lightly_studio.resolvers import video_resolver

        video_table = video_resolver.get_by_id(
            session=db_session, sample_id=video_with_frames.video_sample_id
        )
        assert video_table is not None

        frame_table = video_frame_resolver.get_by_id(
            session=db_session, sample_id=video_with_frames.frame_sample_ids[0]
        )
        assert frame_table is not None

        video_view = VideoView.from_video_table(
            video=video_table, frame=frame_table, similarity_score=0.85
        )

        assert video_view.frame is not None
        assert video_view.frame.frame_number == 0
        assert video_view.frame.frame_timestamp_s == 0.0
        assert video_view.frame.sample_id == frame_table.sample_id
        assert video_view.frame.sample.sample_id == frame_table.sample_id
        assert video_view.similarity_score == 0.85
