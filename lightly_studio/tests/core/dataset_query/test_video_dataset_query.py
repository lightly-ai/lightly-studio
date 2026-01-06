from __future__ import annotations

from pathlib import Path

import pytest

from lightly_studio.core.dataset_query import AND
from lightly_studio.core.dataset_query.video_sample_field import VideoSampleField
from lightly_studio.core.video_dataset import VideoDataset
from tests.core.test_add_videos import _create_temp_video


class TestVideoDatasetQuery:
    def test_dataset_add_videos_from_path__valid(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        _create_temp_video(
            output_path=tmp_path / "test_video_1.mp4",
            width=640,
            height=480,
            num_frames=30,
            fps=2,
        )
        _create_temp_video(
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
