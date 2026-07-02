from __future__ import annotations

import pytest

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_frame_dataset import VideoFrameDataset
from lightly_studio.resolvers import collection_resolver
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


class TestVideoFrameSample:
    def test_field_reads(
        self,
        patch_collection: None,  # noqa: ARG002
    ) -> None:
        dataset = VideoDataset.create(name="test_dataset")
        result = create_video_with_frames(
            session=dataset.session,
            collection_id=dataset.collection_id,
            video=VideoStub(path="/data/a.mp4", width=640, height=480, duration_s=1.0, fps=3.0),
        )
        frame_collection = collection_resolver.get_by_id(
            session=dataset.session, collection_id=result.video_frames_collection_id
        )
        assert frame_collection is not None
        frames = VideoFrameDataset(collection=frame_collection)
        frame = frames.get_sample(result.frame_sample_ids[1])

        assert frame.frame_number == 1
        assert frame.frame_timestamp_s == pytest.approx(1 / 3.0)
        assert frame.frame_timestamp_pts == 1
        assert frame.rotation_deg == 0
