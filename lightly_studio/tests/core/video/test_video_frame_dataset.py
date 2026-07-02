from __future__ import annotations

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_frame_dataset import VideoFrameDataset
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.resolvers import collection_resolver
from tests.resolvers.video.helpers import (
    VideoStub,
    VideoWithFrames,
    create_video_with_frames,
)


def _frame_dataset(dataset: VideoDataset, result: VideoWithFrames) -> VideoFrameDataset:
    """Build a VideoFrameDataset directly from the frame child collection."""
    frame_collection = collection_resolver.get_by_id(
        session=dataset.session, collection_id=result.video_frames_collection_id
    )
    assert frame_collection is not None
    return VideoFrameDataset(collection=frame_collection)


class TestVideoFrameDataset:
    def test_iterates_video_frame_samples(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="test_dataset")
        result = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", duration_s=1.0, fps=3.0),
        )

        frames = _frame_dataset(dataset, result)

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
        frame = _frame_dataset(dataset, result).get_sample(sample_id)

        assert isinstance(frame, VideoFrameSample)
        assert frame.sample_id == sample_id
