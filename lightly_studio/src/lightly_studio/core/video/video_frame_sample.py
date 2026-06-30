"""Definition of VideoFrameSample class, representing a dataset video frame sample."""

from sqlmodel import col

from lightly_studio.core.db_field import DBField
from lightly_studio.core.sample import Sample
from lightly_studio.models.video import VideoFrameTable


class VideoFrameSample(Sample):
    """Interface to a dataset video frame sample.

    Frame properties are directly accessible as attributes of this class.
    ```python
    print(f"Frame number: {sample.frame_number}")
    print(f"Frame timestamp (seconds): {sample.frame_timestamp_s}")
    ```
    """

    frame_number = DBField(col(VideoFrameTable.frame_number))
    frame_timestamp_s = DBField(col(VideoFrameTable.frame_timestamp_s))
    frame_timestamp_pts = DBField(col(VideoFrameTable.frame_timestamp_pts))
    rotation_deg = DBField(col(VideoFrameTable.rotation_deg))

    def __init__(self, inner: VideoFrameTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The VideoFrameTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)
