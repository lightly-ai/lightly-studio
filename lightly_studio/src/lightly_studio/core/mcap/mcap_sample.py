"""Definition of McapSample class, representing a dataset mcap locator sample."""

from sqlmodel import col

from lightly_studio.core.db_field import DBField
from lightly_studio.core.sample import Sample
from lightly_studio.models.mcap import McapTable


class McapSample(Sample):
    """Interface to a dataset mcap locator sample.

    Stores a seek key into an ``.mcap`` file, not pixels or point clouds.
    ```python
    print(f"Sample channel id: {sample.channel_id}")
    print(f"Sample log time: {sample.log_time_ns}")
    ```
    """

    channel_id = DBField(col(McapTable.channel_id))
    """MCAP channel id, unique within the source bag"""
    log_time_ns = DBField(col(McapTable.log_time_ns))
    """MCAP log time, in nanoseconds"""
    capture_timestamp_ns = DBField(col(McapTable.capture_timestamp_ns))
    """Sensor/header capture timestamp, in nanoseconds"""
    keyframe_log_time_ns = DBField(col(McapTable.keyframe_log_time_ns))
    """Log time of the keyframe to seek to before decoding. Required for camera channels."""

    created_at = DBField(col(McapTable.created_at))
    """Creation timestamp"""
    updated_at = DBField(col(McapTable.updated_at))
    """Timestamp of the latest update"""

    def __init__(self, inner: McapTable) -> None:
        """Initialize the Sample.

        Args:
            inner: The McapTable SQLAlchemy model instance.
        """
        self.inner = inner
        super().__init__(sample_table=inner.sample)
