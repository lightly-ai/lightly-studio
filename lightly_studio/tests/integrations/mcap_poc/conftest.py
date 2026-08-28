"""Fixtures for the MCAP processing proof-of-concept tests."""

from __future__ import annotations

import struct
from collections.abc import Generator, Sequence
from pathlib import Path
from typing import Any

import pytest
from mcap_ros2.writer import Writer

from lightly_studio.integrations.mcap_poc import reader

POINT_CLOUD2_MSGDEF = """\
std_msgs/Header header
uint32 height
uint32 width
sensor_msgs/PointField[] fields
bool is_bigendian
uint32 point_step
uint32 row_step
uint8[] data
bool is_dense

================================================================================
MSG: std_msgs/Header
builtin_interfaces/Time stamp
string frame_id

================================================================================
MSG: builtin_interfaces/Time
int32 sec
uint32 nanosec

================================================================================
MSG: sensor_msgs/PointField
string name
uint32 offset
uint8 datatype
uint32 count
"""

STRING_MSGDEF = "string data\n"


@pytest.fixture(autouse=True)
def _clear_source_cache() -> Generator[None, None, None]:
    reader.clear_source_cache()
    yield
    reader.clear_source_cache()


@pytest.fixture
def point_cloud_mcap(tmp_path: Path) -> Path:
    """Write a two-frame ROS 2 PointCloud2 recording with zstd-compressed chunks."""
    path = tmp_path / "sample.mcap"
    with path.open("wb") as stream:
        writer = Writer(stream)
        schema = writer.register_msgdef("sensor_msgs/msg/PointCloud2", POINT_CLOUD2_MSGDEF)
        writer.write_message(
            "/lidar/points",
            schema,
            _point_cloud(points=[(1, 2, 3, 4), (float("nan"), 5, 6, 7)]),
            log_time=100,
        )
        writer.write_message(
            "/lidar/points", schema, _point_cloud(points=[(8, 9, 10, 11)]), log_time=200
        )
        writer.finish()
    return path


@pytest.fixture
def string_only_mcap(tmp_path: Path) -> Path:
    """Write a recording that contains no point-cloud topics."""
    path = tmp_path / "strings.mcap"
    with path.open("wb") as stream:
        writer = Writer(stream)
        schema = writer.register_msgdef("std_msgs/msg/String", STRING_MSGDEF)
        writer.write_message("/notes", schema, {"data": "hello"}, log_time=100)
        writer.finish()
    return path


def _point_cloud(points: Sequence[tuple[float, float, float, float]]) -> dict[str, Any]:
    data = b"".join(struct.pack("<ffff", *point) for point in points)
    names = ("x", "y", "z", "intensity")
    return {
        "header": {"stamp": {"sec": 1, "nanosec": 2}, "frame_id": "lidar"},
        "height": 1,
        "width": len(points),
        "fields": [
            {"name": name, "offset": index * 4, "datatype": 7, "count": 1}
            for index, name in enumerate(names)
        ],
        "is_bigendian": False,
        "point_step": 16,
        "row_step": 16 * len(points),
        "data": data,
        "is_dense": False,
    }
