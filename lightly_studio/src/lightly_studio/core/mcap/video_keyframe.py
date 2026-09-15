"""Keyframe detection in compressed video payloads.

A video frame can only be decoded starting from the keyframe it depends on, so a
frame locator carries the log time of that keyframe. Finding keyframes needs the
compressed bitstream, which is why the payload is read here and nowhere else. The
payload never leaves this module.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from lightly_studio.core.mcap import message_fields

_DATA_FIELDS = ("data",)
_FORMAT_FIELDS = ("format",)

_H264_FORMATS = frozenset({"h264", "avc", "avc1"})
_H265_FORMATS = frozenset({"h265", "hevc", "hvc1"})

# NAL unit start code of an Annex B byte stream. Also matches the four byte variant
# `00 00 00 01`, whose last three bytes are the same.
_START_CODE = b"\x00\x00\x01"

# An H.264 instantaneous decoder refresh picture.
_H264_NAL_TYPE_IDR = 5

# The H.265 intra random access point pictures, from BLA_W_LP to RSV_IRAP_VCL23.
_H265_NAL_TYPE_IRAP_FIRST = 16
_H265_NAL_TYPE_IRAP_LAST = 23


def is_keyframe_message(decoded_message: Any) -> bool:
    """Returns whether a decoded video message holds a keyframe.

    Args:
        decoded_message: A decoded compressed video message.

    Returns:
        Whether the message holds a keyframe. `False` if the payload or its format
        cannot be read, for example because the format is not supported.
    """
    data = message_fields.get_field(decoded_message, _DATA_FIELDS)
    video_format = message_fields.get_field(decoded_message, _FORMAT_FIELDS)
    if not isinstance(data, bytes) or not isinstance(video_format, str):
        return False
    if not is_format_supported(video_format):
        return False
    return is_keyframe(data=data, video_format=video_format)


def is_format_supported(video_format: str) -> bool:
    """Returns whether keyframes can be detected in a video format.

    Args:
        video_format: The video format as recorded in the message, e.g. `h265`.

    Returns:
        Whether `is_keyframe` accepts the format.
    """
    normalized = _normalize_format(video_format)
    return normalized in _H264_FORMATS or normalized in _H265_FORMATS


def is_keyframe(data: bytes, video_format: str) -> bool:
    """Returns whether a compressed video payload holds a keyframe.

    The payload is expected in Annex B format, which is what MCAP recordings of
    compressed video use.

    Args:
        data: The compressed payload of a single video frame.
        video_format: The video format of the payload, e.g. `h265`.

    Returns:
        Whether the payload holds a keyframe, meaning a frame that can be decoded
        without any preceding frame.

    Raises:
        ValueError: If keyframes cannot be detected in the format.
    """
    normalized = _normalize_format(video_format)
    if normalized in _H264_FORMATS:
        return any(
            nal_header & 0x1F == _H264_NAL_TYPE_IDR for nal_header in _iter_nal_headers(data)
        )
    if normalized in _H265_FORMATS:
        return any(
            _H265_NAL_TYPE_IRAP_FIRST <= (nal_header >> 1) & 0x3F <= _H265_NAL_TYPE_IRAP_LAST
            for nal_header in _iter_nal_headers(data)
        )
    raise ValueError(f"Cannot detect keyframes in video format '{video_format}'.")


def _normalize_format(video_format: str) -> str:
    """Returns the video format in lower case and without surrounding whitespace."""
    return video_format.strip().lower()


def _iter_nal_headers(data: bytes) -> Iterator[int]:
    """Yields the first header byte of every NAL unit in an Annex B byte stream.

    Args:
        data: An Annex B byte stream.

    Yields:
        The byte that follows each start code. It holds the NAL unit type in both
        H.264 and H.265.
    """
    offset = 0
    while True:
        start_code_at = data.find(_START_CODE, offset)
        if start_code_at == -1:
            return
        header_at = start_code_at + len(_START_CODE)
        if header_at >= len(data):
            return
        yield data[header_at]
        offset = header_at
