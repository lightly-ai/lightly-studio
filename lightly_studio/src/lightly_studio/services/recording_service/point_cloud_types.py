"""Types and constants shared by point-cloud decoding helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PointCloudPayload:
    """Serialized point data ready to serve over HTTP."""

    data: bytes
    log_time_ns: int


@dataclass(frozen=True)
class PointCloudLayout:
    """Byte layout shared by every field of one PointCloud2 message."""

    width: int
    height: int
    point_step: int
    row_step: int
    endian: Literal[">", "<"]


@dataclass(frozen=True)
class PointCloudFrameMetadata:
    """Frame-level metadata attached to a serialized point cloud."""

    channel_id: int
    topic: str
    log_time_ns: int
    frame_id: str
    source_point_count: int


FLOAT32_DATATYPE = 7
POINT_FIELD_DTYPES: dict[int, str] = {
    1: "i1",
    2: "u1",
    3: "<i2",
    4: "<u2",
    5: "<i4",
    6: "<u4",
    FLOAT32_DATATYPE: "<f4",
    8: "<f8",
}
# The sRGB component below which the transfer function is linear.
SRGB_LINEAR_THRESHOLD = 0.04045
