from __future__ import annotations

import pytest

from lightly_studio.core.dataset_query import OrderByField
from lightly_studio.core.dataset_query.video_frame_sample_field import VideoFrameSampleField
from lightly_studio.core.video.video_dataset import VideoDataset
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


@pytest.fixture
def dataset(patch_collection: None) -> VideoDataset:  # noqa: ARG001
    """Video A (frames 0-2) and video B (frames 0-1) => 5 frames."""
    dataset = VideoDataset.create(name="ds")
    for path, fps in (("/data/a.mp4", 3.0), ("/data/b.mp4", 2.0)):
        create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path=path, duration_s=1.0, fps=fps),
        )
    return dataset


class TestVideoFrameDatasetQuery:
    def test_match_frame_number(self, dataset: VideoDataset) -> None:
        result = dataset.frames().match(VideoFrameSampleField.frame_number > 0).to_list()

        # video A: frames 1, 2 ; video B: frame 1 => 3 frames
        assert len(result) == 3
        assert all(frame.frame_number > 0 for frame in result)

    @pytest.mark.parametrize(
        ("order_by_field", "reverse"),
        [
            (OrderByField(VideoFrameSampleField.frame_number), False),
            (OrderByField(VideoFrameSampleField.frame_number).desc(), True),
        ],
    )
    def test_ordering(
        self, dataset: VideoDataset, order_by_field: OrderByField, reverse: bool
    ) -> None:
        frame_numbers = [frame.frame_number for frame in dataset.frames().order_by(order_by_field)]
        assert frame_numbers == sorted(frame_numbers, reverse=reverse)

    def test_filter_by_parent_video_attribute(self, dataset: VideoDataset) -> None:
        frames = dataset.frames()

        # Comparable field: only video A's 3 frames (0, 1, 2).
        by_path = frames.match(
            VideoFrameSampleField.parent_video.file_path_abs == "/data/a.mp4"
        ).to_list()
        assert len(by_path) == 3
        assert all(frame.parent_video.file_path_abs == "/data/a.mp4" for frame in by_path)

        # Numerical field: video A has fps 3.0, video B fps 2.0 => only A's 3 frames.
        by_fps = dataset.frames().match(VideoFrameSampleField.parent_video.fps > 2.5).to_list()
        assert len(by_fps) == 3
        assert all(frame.parent_video.file_path_abs == "/data/a.mp4" for frame in by_fps)

    def test_filter_by_parent_video_tag(self, dataset: VideoDataset) -> None:
        for video in dataset.query():
            if video.file_path_abs == "/data/a.mp4":
                video.add_tag("reviewed")

        reviewed = (
            dataset.frames()
            .match(VideoFrameSampleField.parent_video.tags.contains("reviewed"))
            .to_list()
        )
        assert len(reviewed) == 3
        assert all(frame.parent_video.file_path_abs == "/data/a.mp4" for frame in reviewed)
