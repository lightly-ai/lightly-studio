"""Definition of VideoFrameSample class, representing a dataset video frame sample."""

from sqlmodel import col

from lightly_studio.core.db_field import DBField
from lightly_studio.core.sample import Sample
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.models.video import VideoFrameTable


class VideoFrameSample(Sample):
    """Interface to a dataset video frame sample.

    Many properties of the sample are directly accessible as attributes of this class.
    ```python
    print(f"Frame number: {sample.frame_number}")
    print(f"Frame timestamp (seconds): {sample.frame_timestamp_s}")
    ```

    The parent video is accessible as a `VideoSample` via the `parent_video` property:
    ```python
    print(f"Parent video file path: {sample.parent_video.file_path_abs}")
    ```
    """

    frame_number = DBField(col(VideoFrameTable.frame_number))
    """Frame number within the parent video"""
    frame_timestamp_s = DBField(col(VideoFrameTable.frame_timestamp_s))
    """Presentation timestamp of the frame in seconds"""
    frame_timestamp_pts = DBField(col(VideoFrameTable.frame_timestamp_pts))
    """Presentation timestamp of the frame in the video's time_base units"""
    rotation_deg = DBField(col(VideoFrameTable.rotation_deg))
    """Rotation of the encoded frame in degrees (0, 90, 180, 270)"""

    def __init__(self, inner: VideoFrameTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The VideoFrameTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)

    @property
    def parent_video(self) -> VideoSample:
        """The parent video this frame belongs to."""
        return VideoSample(inner=self.inner.video)
