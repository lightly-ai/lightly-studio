"""Decoding a single displayable frame from a compressed video message.

Handles `foxglove_msgs/msg/CompressedVideo` (and the equivalent Foxglove schema),
which carry Annex B H.264 or H.265 bitstreams. A single message may be a keyframe or
a delta frame; the caller is responsible for locating the right message via
`McapFileReader.get_decoded_message_near`.

The frame is decoded with PyAV (libav) and re-encoded as JPEG so the result is
directly servable from an HTTP endpoint without any further processing.
"""

from __future__ import annotations

import io
from typing import Any

import av
from PIL import Image

from lightly_studio.core.mcap import message_fields
from lightly_studio.core.mcap.errors import McapAccessError

_DATA_FIELDS = ("data",)
_FORMAT_FIELDS = ("format",)

_H264_FORMATS = frozenset({"h264", "avc", "avc1"})
_H265_FORMATS = frozenset({"h265", "hevc", "hvc1"})

JPEG_QUALITY = 85


def from_decoded_message(
    decoded_message: Any,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """Decodes the first decodable frame from a compressed video message.

    Wraps the Annex B payload in a minimal container and feeds it through PyAV so
    that the codec can decode the frame without needing preceding frames in the
    stream. Only keyframes are fully decodable in isolation; delta frames that
    arrive without a preceding keyframe will either produce a corrupted image or
    raise an error — callers should prefer to pass a keyframe message.

    Args:
        decoded_message: A decoded compressed video message with `data` (bytes,
            Annex B) and `format` (str, e.g. ``"h265"``) fields.
        width: If set, resize the output to this width in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        height: If set, resize the output to this height in pixels. Aspect ratio is
            preserved when only one of `width` / `height` is given.
        quality: JPEG quality (1-95). Defaults to `JPEG_QUALITY`.

    Returns:
        JPEG-encoded bytes of the decoded frame.

    Raises:
        McapAccessError: If the message fields are missing, the video format is not
            supported (not H.264 or H.265), or PyAV cannot decode the payload.
    """
    data = message_fields.require_field(decoded_message, _DATA_FIELDS)
    video_format = message_fields.require_field(decoded_message, _FORMAT_FIELDS)
    if not isinstance(data, (bytes, bytearray)):
        raise McapAccessError(
            f"Compressed video message has a non-byte 'data' field: {type(data).__name__}."
        )
    if not isinstance(video_format, str):
        raise McapAccessError(
            f"Compressed video message has a non-string 'format' field: "
            f"{type(video_format).__name__}."
        )
    codec_name = _codec_name(video_format)
    return _decode_annex_b(
        data=bytes(data),
        codec_name=codec_name,
        width=width,
        height=height,
        quality=quality,
    )


def _codec_name(video_format: str) -> str:
    """Returns the libav codec name for a recorded format string.

    Raises:
        McapAccessError: If the format is not H.264 or H.265.
    """
    normalized = video_format.strip().lower()
    if normalized in _H264_FORMATS:
        return "h264"
    if normalized in _H265_FORMATS:
        return "hevc"
    raise McapAccessError(
        f"Unsupported compressed video format: '{video_format}'. "
        f"Only H.264 and H.265 are supported."
    )


def _decode_annex_b(
    data: bytes,
    codec_name: str,
    width: int | None = None,
    height: int | None = None,
    quality: int = JPEG_QUALITY,
) -> bytes:
    """Decodes the first frame of an Annex B payload and returns it as JPEG.

    Args:
        data: The Annex B compressed payload of a single video frame.
        codec_name: The libav codec name, e.g. ``"hevc"`` or ``"h264"``.
        width: Output width in pixels; preserves aspect ratio when `height` is unset.
        height: Output height in pixels; preserves aspect ratio when `width` is unset.
        quality: JPEG quality (1-95).

    Returns:
        JPEG-encoded bytes of the decoded frame.

    Raises:
        McapAccessError: If PyAV cannot decode any frame from the payload.
    """
    try:
        codec = av.CodecContext.create(codec_name, "r")
        # Each MCAP message is one complete Annex B access unit, so wrap it directly
        # as a packet rather than using codec.parse(), which buffers across calls and
        # returns nothing for a single isolated payload.
        packet = av.Packet(data)
        frames = codec.decode(packet)  # type: ignore[attr-defined]
        for frame in frames:
            image = Image.fromarray(frame.to_ndarray(format="rgb24"))
            if width is not None or height is not None:
                image = _resize(image, width=width, height=height)
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality, subsampling=2)
            return buffer.getvalue()
    except av.FFmpegError as exc:
        raise McapAccessError(f"PyAV could not decode the {codec_name} payload: {exc}") from exc
    raise McapAccessError(f"No decodable frame found in the {codec_name} payload.")


def _resize(image: Image.Image, width: int | None, height: int | None) -> Image.Image:
    """Resizes an image, preserving aspect ratio when only one dimension is given."""
    orig_w, orig_h = image.size
    if width is None:
        assert height is not None
        width = max(1, round(orig_w * height / orig_h))
    elif height is None:
        height = max(1, round(orig_h * width / orig_w))
    return image.resize((width, height), Image.Resampling.LANCZOS)
