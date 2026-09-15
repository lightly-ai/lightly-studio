"""Builds small MCAP files to read in the tests.

The fixtures use ROS 2 message definitions because they can be written without any
compiled schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcap.writer import Writer as McapWriter
from mcap_ros2.writer import Writer

CAMERA_VIDEO_TOPIC = "/cam/front/compressed_video"
LIDAR_POINTS_TOPIC = "/lidar/points"
CAMERA_FRAME_ID = "cam_front_optical"
LIDAR_FRAME_ID = "livox_front_left"

# The log times of the video frames, one frame every 100 ms. The frames at index 0 and
# 2 are keyframes.
VIDEO_LOG_TIMES_NS = (1_000_000_000, 1_100_000_000, 1_200_000_000, 1_300_000_000)
VIDEO_KEYFRAME_LOG_TIMES_NS = (1_000_000_000, 1_200_000_000)

LIDAR_LOG_TIMES_NS = (1_050_000_000, 1_250_000_000)

_HEADER_MSGDEF = """
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
"""

_COMPRESSED_VIDEO_MSGDEF = """
builtin_interfaces/Time timestamp
string frame_id
uint8[] data
string format
"""

_POINT_CLOUD_MSGDEF = (
    """
std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense
"""
    + _HEADER_MSGDEF
    + """
================================================================================
MSG: sensor_msgs/PointField
string name
uint32 offset
uint8 datatype
uint32 count
"""
)


def write_mcap(path: Path) -> Path:
    """Writes an indexed MCAP file with a camera and a lidar.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    writer = Writer(output=str(path))
    video_schema = writer.register_msgdef(
        datatype="foxglove_msgs/msg/CompressedVideo", msgdef_text=_COMPRESSED_VIDEO_MSGDEF
    )
    point_cloud_schema = writer.register_msgdef(
        datatype="sensor_msgs/msg/PointCloud2", msgdef_text=_POINT_CLOUD_MSGDEF
    )

    for log_time_ns in VIDEO_LOG_TIMES_NS:
        writer.write_message(
            topic=CAMERA_VIDEO_TOPIC,
            schema=video_schema,
            message=_compressed_video_message(log_time_ns=log_time_ns),
            log_time=log_time_ns,
        )
    for log_time_ns in LIDAR_LOG_TIMES_NS:
        writer.write_message(
            topic=LIDAR_POINTS_TOPIC,
            schema=point_cloud_schema,
            message=_point_cloud_message(),
            log_time=log_time_ns,
        )
    writer.finish()
    return path


def write_mcap_with_undecodable_video(path: Path) -> Path:
    """Writes an MCAP whose video topic has no decoder.

    The schema name marks the topic as video, but its encoding is unknown, so no
    decoder factory can read the payloads and no keyframe can be detected.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    with path.open("wb") as stream:
        writer = McapWriter(output=stream)
        writer.start()
        schema_id = writer.register_schema(
            name="foxglove_msgs/msg/CompressedVideo", encoding="unknown", data=b""
        )
        channel_id = writer.register_channel(
            topic=CAMERA_VIDEO_TOPIC, message_encoding="unknown", schema_id=schema_id
        )
        for log_time_ns in VIDEO_LOG_TIMES_NS:
            writer.add_message(
                channel_id=channel_id,
                log_time=log_time_ns,
                publish_time=log_time_ns,
                data=h265_keyframe(),
            )
        writer.finish()
    return path


def h265_keyframe(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.265 frame holding an IDR picture."""
    return b"\x00\x00\x00\x01\x26\x01" + payload


def h265_delta_frame(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.265 frame holding a trailing picture."""
    return b"\x00\x00\x00\x01\x02\x01" + payload


def h264_keyframe(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.264 frame holding an IDR picture."""
    return b"\x00\x00\x00\x01\x65" + payload


def h264_delta_frame(payload: bytes = b"\x00\x01\x02") -> bytes:
    """Returns an Annex B H.264 frame holding a non-IDR picture."""
    return b"\x00\x00\x00\x01\x41" + payload


def _compressed_video_message(log_time_ns: int) -> dict[str, Any]:
    is_keyframe = log_time_ns in VIDEO_KEYFRAME_LOG_TIMES_NS
    return {
        "timestamp": _time(log_time_ns),
        "frame_id": CAMERA_FRAME_ID,
        "data": h265_keyframe() if is_keyframe else h265_delta_frame(),
        "format": "h265",
    }


def _point_cloud_message() -> dict[str, Any]:
    return {
        "header": {"stamp": _time(LIDAR_LOG_TIMES_NS[0]), "frame_id": LIDAR_FRAME_ID},
        "height": 1,
        "width": 1,
        "fields": [{"name": "x", "offset": 0, "datatype": 7, "count": 1}],
        "is_bigendian": False,
        "point_step": 4,
        "row_step": 4,
        "data": b"\x00\x00\x00\x00",
        "is_dense": True,
    }


def _time(log_time_ns: int) -> dict[str, int]:
    return {"sec": log_time_ns // 1_000_000_000, "nanosec": log_time_ns % 1_000_000_000}
