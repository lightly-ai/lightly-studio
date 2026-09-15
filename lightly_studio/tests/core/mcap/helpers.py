"""Builds small MCAP files to read in the tests.

The fixtures use ROS 2 message definitions because they can be written without any
compiled schemas.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcap_ros2.writer import Writer

LIDAR_POINTS_TOPIC = "/lidar/points"
LIDAR_FRAME_ID = "livox_front_left"

LIDAR_LOG_TIMES_NS = (1_050_000_000, 1_250_000_000)

_HEADER_MSGDEF = """
================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id
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
    """Writes an indexed MCAP file with a lidar topic.

    Args:
        path: The path to write the file to.

    Returns:
        The path of the written file.
    """
    writer = Writer(output=str(path))
    point_cloud_schema = writer.register_msgdef(
        datatype="sensor_msgs/msg/PointCloud2", msgdef_text=_POINT_CLOUD_MSGDEF
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
