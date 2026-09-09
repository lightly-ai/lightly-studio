"""Tests for reading an MCAP recording's index."""

import io

import pytest
from mcap.reader import make_reader
from mcap.writer import IndexType, Writer

from lightly_studio.core.mcap import recording_index

FIRST_LOG_TIME_NS = 1789000000000000001


def _recording(*, indexed: bool = True) -> io.BytesIO:
    """A tiny recording with one point-cloud channel and one unsupported channel.

    Without a summary section there is nothing to seek by, which is the case the workspace
    cannot use at all.
    """
    stream = io.BytesIO()
    writer = (
        Writer(stream)
        if indexed
        else Writer(
            stream,
            index_types=IndexType.NONE,
            repeat_channels=False,
            repeat_schemas=False,
            use_statistics=False,
            use_summary_offsets=False,
        )
    )
    writer.start(profile="ros2", library="test")

    lidar_schema = writer.register_schema(
        name="sensor_msgs/msg/PointCloud2", encoding="ros2msg", data=b""
    )
    lidar_channel = writer.register_channel(
        topic="/lidar", message_encoding="cdr", schema_id=lidar_schema
    )
    imu_schema = writer.register_schema(name="sensor_msgs/msg/Imu", encoding="ros2msg", data=b"")
    imu_channel = writer.register_channel(
        topic="/imu", message_encoding="cdr", schema_id=imu_schema
    )

    for offset in range(3):
        writer.add_message(
            channel_id=lidar_channel,
            log_time=FIRST_LOG_TIME_NS + offset,
            data=b"points",
            publish_time=FIRST_LOG_TIME_NS + offset - 1,
        )
    writer.add_message(
        channel_id=imu_channel,
        log_time=FIRST_LOG_TIME_NS,
        data=b"imu",
        publish_time=FIRST_LOG_TIME_NS,
    )
    writer.finish()
    stream.seek(0)
    return stream


def test_find_point_cloud_channels() -> None:
    """Only ROS 2 CDR point-cloud channels are reported, with their message counts."""
    channels = recording_index.find_point_cloud_channels(make_reader(_recording()))

    assert len(channels) == 1
    assert channels[0].topic == "/lidar"
    assert channels[0].schema_name == "sensor_msgs/msg/PointCloud2"
    assert channels[0].message_count == 3


def test_find_point_cloud_channels__without_a_summary() -> None:
    reader = make_reader(_recording(indexed=False))

    with pytest.raises(ValueError, match="no summary section"):
        recording_index.find_point_cloud_channels(reader)


def test_iter_point_cloud_frames() -> None:
    """Every message on the topic becomes a locator, keeping its exact log time."""
    reader = make_reader(_recording())

    frames = list(recording_index.iter_point_cloud_frames(reader, topic="/lidar"))

    assert [frame.log_time_ns for frame in frames] == [
        FIRST_LOG_TIME_NS,
        FIRST_LOG_TIME_NS + 1,
        FIRST_LOG_TIME_NS + 2,
    ]
    assert frames[0].capture_timestamp_ns == FIRST_LOG_TIME_NS - 1
    assert frames[0].keyframe_log_time_ns is None


def test_iter_point_cloud_frames__limit() -> None:
    reader = make_reader(_recording())

    frames = list(recording_index.iter_point_cloud_frames(reader, topic="/lidar", limit=2))

    assert [frame.log_time_ns for frame in frames] == [FIRST_LOG_TIME_NS, FIRST_LOG_TIME_NS + 1]


def test_iter_point_cloud_frames__unknown_topic() -> None:
    reader = make_reader(_recording())

    assert list(recording_index.iter_point_cloud_frames(reader, topic="/absent")) == []
