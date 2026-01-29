from __future__ import annotations

from pathlib import Path

import pytest

from lightly_studio.core.dataset_query import AND, OrderByField
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.core.video_dataset import VideoDataset
from tests.resolvers.video.helpers import create_video_file


class TestVideoDatasetQuery:
    def test_match_query(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        create_video_file(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        create_video_file(
            output_path=tmp_path / "test_video_0.mp4",
            width=1024,
            height=768,
            num_frames=30,
            fps=3,
        )

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_path(path=tmp_path)
        query = dataset.query().match(VideoSampleField.fps == 3)
        it = iter(query)
        assert next(it).fps == 3
        with pytest.raises(StopIteration):
            next(it)

        query = dataset.query().match(
            AND(VideoSampleField.width == 640, VideoSampleField.height == 480)
        )
        it = iter(query)
        assert next(it).width == 640
        with pytest.raises(StopIteration):
            next(it)

        query = dataset.query().match(VideoSampleField.file_name == "test_video_1.mp4")
        it = iter(query)
        assert next(it).file_name == "test_video_1.mp4"
        with pytest.raises(StopIteration):
            next(it)

        query = dataset.query().match(VideoSampleField.duration_s == 10)
        it = iter(query)
        assert next(it).file_name == "test_video_0.mp4"
        with pytest.raises(StopIteration):
            next(it)

    def test_ordering(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        create_video_file(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=30,
        )
        create_video_file(
            output_path=tmp_path / "test_video_0.mp4",
            width=1024,
            height=768,
            num_frames=30,
            fps=20,
        )

        dataset = VideoDataset.create(name="test_dataset")
        dataset.add_videos_from_path(path=tmp_path)
        query = dataset.order_by(OrderByField(VideoSampleField.fps))
        it = iter(query)
        assert next(it).fps == 20
        assert next(it).fps == 30
        with pytest.raises(StopIteration):
            next(it)
