"""Decode the payload of a ROS 2 sensor_msgs/CompressedImage message."""

from __future__ import annotations

import struct


def decode_compressed_image(data: bytes) -> tuple[bytes, str]:
    """Return image bytes and a MIME type from serialized CompressedImage data."""
    reader = _CdrReader(data)
    reader.skip(4)
    reader.skip(8)
    reader.string()  # header.frame_id
    format_ = reader.string().lower()
    image = reader.read_bytes()
    if "png" in format_:
        return image, "image/png"
    if "jpeg" in format_ or "jpg" in format_:
        return image, "image/jpeg"
    raise ValueError(f"Unsupported compressed image format: {format_ or 'unknown'}")


class _CdrReader:
    """Small bounds-checked CDR reader for CompressedImage."""

    def __init__(self, data: bytes) -> None:
        self.data = data
        self.offset = 0

    def skip(self, size: int) -> None:
        self._take(size)

    def u32(self) -> int:
        self._align(4)
        return int(struct.unpack_from("<I", self._take(4))[0])

    def string(self) -> str:
        raw = self._take(self.u32())
        return raw[:-1].decode("utf-8") if raw.endswith(b"\0") else raw.decode("utf-8")

    def read_bytes(self) -> bytes:
        return self._take(self.u32())

    def _align(self, alignment: int) -> None:
        self.offset = (self.offset + alignment - 1) & ~(alignment - 1)

    def _take(self, size: int) -> bytes:
        end = self.offset + size
        if end > len(self.data):
            raise ValueError("CompressedImage message is truncated")
        result = self.data[self.offset : end]
        self.offset = end
        return result
