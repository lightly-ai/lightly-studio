"""Definition of VideoSample class, representing a dataset video sample."""

from sqlmodel import col

from lightly_studio.core.db_field import DBField
from lightly_studio.core.sample import Sample
from lightly_studio.models.video import VideoTable


class VideoSample(Sample):
    """Interface to a dataset video sample.

    Many properties of the sample are directly accessible as attributes of this class.
    ```python
    print(f"Sample file name: {sample.file_name}")
    print(f"Sample file path: {sample.file_path_abs}")
    print(f"Sample width: {sample.width}")
    print(f"Sample height: {sample.height}")
    print(f"Sample duration (seconds): {sample.duration_s}")
    print(f"Sample FPS: {sample.fps}")
    ```
    """

    file_name = DBField(col(VideoTable.file_name))
    width = DBField(col(VideoTable.width))
    height = DBField(col(VideoTable.height))
    file_path_abs = DBField(col(VideoTable.file_path_abs))

    duration_s = DBField(col(VideoTable.duration_s))
    fps = DBField(col(VideoTable.fps))

    def __init__(self, inner: VideoTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The VideoTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)
