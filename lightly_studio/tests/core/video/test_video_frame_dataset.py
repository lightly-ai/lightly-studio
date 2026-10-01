from __future__ import annotations

from pathlib import Path

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_frame_dataset import VideoFrameDataset
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from tests.resolvers.video.helpers import (
    VideoStub,
    create_video_file,
    create_video_with_frames,
)


class TestVideoFrameDataset:
    def test_frames_iterates_video_frame_samples(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="test_dataset")
        result = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=3.0),
        )

        frames = dataset.frames()

        assert isinstance(frames, VideoFrameDataset)
        frame_list = list(frames)
        assert len(frame_list) == len(result.frame_sample_ids) == 3
        assert all(isinstance(frame, VideoFrameSample) for frame in frame_list)

    def test_get_sample(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="test_dataset")
        result = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=3.0),
        )

        sample_id = result.frame_sample_ids[0]
        frame = dataset.frames().get_sample(sample_id)

        assert isinstance(frame, VideoFrameSample)
        assert frame.sample_id == sample_id

    def test_frames_empty_without_videos(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="empty_dataset")
        assert list(dataset.frames()) == []

    def test_frames_end_to_end_from_real_videos(
        self,
        patch_collection: None,  # noqa: ARG002
        tmp_path: Path,
    ) -> None:
        create_video_file(
            output_path=tmp_path / "vid.mp4",
            width=320,
            height=240,
            num_frames=5,
            fps=5,
        )

        dataset = VideoDataset.create(name="real_dataset")
        dataset.add_videos_from_path(path=tmp_path, embed=False, embed_frames=False)

        frame_list = list(dataset.frames())
        assert len(frame_list) > 0
        frame_numbers = [frame.frame_number for frame in frame_list]
        assert frame_numbers == sorted(frame_numbers)
        assert all(frame.parent_video.file_name == "vid.mp4" for frame in frame_list)
