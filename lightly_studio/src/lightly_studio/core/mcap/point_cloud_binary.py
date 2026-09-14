"""Convert one ROS 2 PointCloud2 message to a compact binary point buffer."""

from __future__ import annotations

import struct
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

_MAGIC = b"LSPC"
_VERSION = 1
_FLOAT32_DATATYPE = 7
_FLOAT64_DATATYPE = 8
_FLOAT32_BYTES = 4


@dataclass(frozen=True)
class PointCloudBinary:
    """Binary point-cloud payload and its metadata."""

    payload: bytes
    timestamp_ns: int
    frame_id: str
    point_count: int
    source_point_count: int


def encode_point_cloud_message(
    data: bytes, *, timestamp_ns: int, point_budget: int = 350_000
) -> PointCloudBinary:
    """Decode a serialized ROS 2 PointCloud2 and encode finite XYZ values.

    The output is ``LSPC`` version 1: magic (4 bytes), version (u8), flags (u8), reserved
    (u16), point count (u32), source point count (u32), timestamp (u64), followed by tightly
    packed little-endian ``Float32`` XYZ triples.
    """
    if point_budget < 1:
        raise ValueError("point_budget must be positive")
    message = _CdrReader(data)
    message.skip(4)
    message.skip(8)
    frame_id = message.string()
    height = message.u32()
    width = message.u32()
    fields = _read_fields(message)
    big_endian = message.u8() != 0
    point_step = message.u32()
    row_step = message.u32()
    point_data = message.read_bytes()
    message.skip(1)

    xyz: list[float] = []
    readers: list[Callable[[bytes, int, bool], float]] = [
        _field_reader(fields, name) for name in ("x", "y", "z")
    ]
    source_count = width * height
    stride = max(1, (source_count + point_budget - 1) // point_budget)
    for index in range(0, source_count, stride):
        offset = (index // width) * row_step + (index % width) * point_step
        values = tuple(reader(point_data, offset, big_endian) for reader in readers)
        if all(isfinite(value) for value in values):
            xyz.extend(values)

    encoded_points = struct.pack(f"<{len(xyz)}f", *xyz) if xyz else b""
    header = struct.pack(
        "<4sBBHIIQ",
        _MAGIC,
        _VERSION,
        0,
        0,
        len(xyz) // 3,
        source_count,
        timestamp_ns,
    )
    return PointCloudBinary(
        payload=header + encoded_points,
        timestamp_ns=timestamp_ns,
        frame_id=frame_id,
        point_count=len(xyz) // 3,
        source_point_count=source_count,
    )


class _CdrReader:
    """Small bounds-checked reader for the PointCloud2 CDR layout."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def skip(self, size: int) -> None:
        self._take(size)

    def u8(self) -> int:
        return int(struct.unpack_from("<B", self._take(1))[0])

    def u32(self) -> int:
        self._align(4)
        return int(struct.unpack_from("<I", self._take(4))[0])

    def string(self) -> str:
        size = self.u32()
        raw = self._take(size)
        return raw[:-1].decode("utf-8") if raw.endswith(b"\0") else raw.decode("utf-8")

    def read_bytes(self) -> bytes:
        size = self.u32()
        return self._take(size)

    def _align(self, alignment: int) -> None:
        self.offset = (self.offset + alignment - 1) & ~(alignment - 1)

    def _take(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise ValueError("PointCloud2 message is truncated")
        result = self.data[self.offset : end]
        self.offset = end
        return result


def _read_fields(reader: _CdrReader) -> dict[str, tuple[int, int, int]]:
    fields: dict[str, tuple[int, int, int]] = {}
    for _ in range(reader.u32()):
        fields[reader.string()] = (reader.u32(), reader.u8(), reader.u32())
    return fields


def _field_reader(
    fields: dict[str, tuple[int, int, int]], name: str
) -> Callable[[bytes, int, bool], float]:
    try:
        offset, datatype, count = fields[name]
    except KeyError as error:
        raise ValueError(f"PointCloud2 requires field '{name}'") from error
    if count != 1 or datatype not in {_FLOAT32_DATATYPE, _FLOAT64_DATATYPE}:
        raise ValueError(f"PointCloud2 field '{name}' must be a scalar float")
    size = _FLOAT32_BYTES if datatype == _FLOAT32_DATATYPE else 8

    def read(data: bytes, point_offset: int, big_endian: bool) -> float:
        if size == _FLOAT32_BYTES:
            format_ = ">f" if big_endian else "<f"
        else:
            format_ = ">d" if big_endian else "<d"
        return float(struct.unpack_from(format_, data, point_offset + offset)[0])

    return read


def add_binary_header_metadata(response_headers: dict[str, str], cloud: PointCloudBinary) -> None:
    """Add metadata needed by a binary-buffer frontend decoder."""
    response_headers.update(
        {
            "X-Point-Cloud-Format": "LSPC/1",
            "X-Point-Cloud-Frame-Id": cloud.frame_id,
            "X-Point-Cloud-Count": str(cloud.point_count),
            "X-Point-Cloud-Source-Count": str(cloud.source_point_count),
        }
    )
