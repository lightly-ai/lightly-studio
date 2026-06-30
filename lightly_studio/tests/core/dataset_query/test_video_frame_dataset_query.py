from __future__ import annotations

from lightly_studio.core.dataset_query import OrderByField
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from tests.resolvers.video.helpers import (
    VideoStub,
    VideoWithFrames,
    create_video_with_frames,
)


def _seed_two_videos(dataset: VideoDataset) -> tuple[VideoWithFrames, VideoWithFrames]:
    """Seed video A (640px, frames 0-2) and video B (1920px, frames 0-1)."""
    video_a = create_video_with_frames(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(path="/data/a.mp4", width=640, height=480, duration_s=1.0, fps=3.0),
    )
    video_b = create_video_with_frames(
        session=dataset.session,
        collection_id=dataset.collection_id,
        video=VideoStub(path="/data/b.mp4", width=1920, height=1080, duration_s=1.0, fps=2.0),
    )
    return video_a, video_b


class TestVideoFrameDatasetQuery:
    def test_total_count(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="ds")
        _seed_two_videos(dataset)
        assert len(list(dataset.frames())) == 5

    def test_match_frame_number(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="ds")
        _seed_two_videos(dataset)

        result = dataset.frames().match(VideoFrameSampleField.frame_number > 0).to_list()

        # video A: frames 1, 2 ; video B: frame 1 => 3 frames
        assert len(result) == 3
        assert all(frame.frame_number > 0 for frame in result)

    def test_ordering(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="ds")
        _seed_two_videos(dataset)

        ascending = [
            frame.frame_number
            for frame in dataset.frames().order_by(OrderByField(VideoFrameSampleField.frame_number))
        ]
        assert ascending == sorted(ascending)

        descending = [
            frame.frame_number
            for frame in dataset.frames().order_by(
                OrderByField(VideoFrameSampleField.frame_number).desc()
            )
        ]
        assert descending == sorted(descending, reverse=True)

    def test_slicing(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="ds")
        _seed_two_videos(dataset)
        assert len(dataset.frames()[:2].to_list()) == 2

    def test_frame_level_tags(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="ds")
        _seed_two_videos(dataset)

        # video A: frames 1, 2 ; video B: frame 1 => 3 frames
        dataset.frames().match(VideoFrameSampleField.frame_number > 0).add_tag("tagged")

        tagged = dataset.frames().match(VideoFrameSampleField.tags.contains("tagged")).to_list()
        assert len(tagged) == 3
