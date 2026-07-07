"""LightlyStudio VideoFrameDataset."""

from __future__ import annotations

from uuid import UUID

from lightly_studio.core.dataset import Dataset
from lightly_studio.core.video.video_frame_sample import VideoFrameSample
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import video_frame_resolver


class VideoFrameDataset(Dataset[VideoFrameSample]):
    """Video frame dataset.

    It is not created or loaded directly. It is obtained from a `VideoDataset` via
    `video_dataset.frames()` and exposes the individual video frames as queryable
    `VideoFrameSample` objects.

    The dataset frames can be accessed directly by iterating over it or slicing it:
    ```python
    from lightly_studio import VideoDataset

    frames = VideoDataset.load("my_dataset").frames()
    first_ten_frames = frames[:10]
    for frame in frames:
        print(frame.frame_number, frame.parent_video.file_name)
    ```

    For filtering or ordering frames first, use the query interface:
    ```python
    from lightly_studio.core.dataset_query import VideoFrameSampleField

    frames = VideoDataset.load("my_dataset").frames()
    query = frames.match(VideoFrameSampleField.frame_number > 10)
    for frame in query:
        ...
    ```
    """

    @staticmethod
    def sample_type() -> SampleType:
        """Returns the sample type."""
        return SampleType.VIDEO_FRAME

    @staticmethod
    def sample_class() -> type[VideoFrameSample]:
        """Returns the sample class."""
        return VideoFrameSample

    def get_sample(self, sample_id: UUID) -> VideoFrameSample:
        """Get a single video frame sample from the dataset by its ID.

        Args:
            sample_id: The UUID of the video frame sample to retrieve.

        Returns:
            A single VideoFrameSample object.
        """
        inner = video_frame_resolver.get_by_id(session=self.session, sample_id=sample_id)
        return VideoFrameSample(inner=inner)
