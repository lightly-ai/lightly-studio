"""Tests for compressed_video.py — decoding CompressedVideo messages to JPEG."""

from __future__ import annotations

import io
from types import SimpleNamespace

import av
import pytest
from av import VideoStream
from PIL import Image

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.errors import McapAccessError


def _h264_keyframe(width: int = 16, height: int = 16) -> bytes:
    """Returns a real decodable H.264 Annex B keyframe."""
    buf = io.BytesIO()
    with av.open(buf, "w", format="h264") as container:
        stream = container.add_stream("libx264", rate=25)
        assert isinstance(stream, VideoStream)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"
        stream.options = {"tune": "zerolatency", "preset": "ultrafast"}
        frame = av.VideoFrame(width, height, "yuv420p")
        frame.pts = 0
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return buf.getvalue()


def _h265_keyframe(width: int = 16, height: int = 16) -> bytes:
    """Returns a real decodable H.265 Annex B keyframe."""
    buf = io.BytesIO()
    with av.open(buf, "w", format="hevc") as container:
        stream = container.add_stream("libx265", rate=25)
        assert isinstance(stream, VideoStream)
        stream.width = width
        stream.height = height
        stream.pix_fmt = "yuv420p"
        stream.options = {
            "tune": "zerolatency",
            "preset": "ultrafast",
            "x265-params": "log-level=none",
        }
        frame = av.VideoFrame(width, height, "yuv420p")
        frame.pts = 0
        for packet in stream.encode(frame):
            container.mux(packet)
        for packet in stream.encode():
            container.mux(packet)
    return buf.getvalue()


def _jpeg_size(data: bytes) -> tuple[int, int]:
    image = Image.open(io.BytesIO(data))
    return image.size  # (width, height)


def test_from_decoded_message__h264() -> None:
    message = SimpleNamespace(data=_h264_keyframe(), format="h264")
    result = compressed_video.from_decoded_message(message)
    assert result[:3] == b"\xff\xd8\xff"  # JPEG magic


def test_from_decoded_message__h265() -> None:
    message = SimpleNamespace(data=_h265_keyframe(), format="h265")
    result = compressed_video.from_decoded_message(message)
    assert result[:3] == b"\xff\xd8\xff"


def test_from_decoded_message__dict_message() -> None:
    message = {"data": _h264_keyframe(), "format": "h264"}
    result = compressed_video.from_decoded_message(message)
    assert result[:3] == b"\xff\xd8\xff"


def test_from_decoded_message__resize_width() -> None:
    message = SimpleNamespace(data=_h264_keyframe(width=32, height=16), format="h264")
    result = compressed_video.from_decoded_message(message, width=8)
    w, h = _jpeg_size(result)
    assert w == 8
    assert h == 4  # aspect ratio preserved: 32/16 → 8/4


def test_from_decoded_message__resize_height() -> None:
    message = SimpleNamespace(data=_h264_keyframe(width=16, height=32), format="h264")
    result = compressed_video.from_decoded_message(message, height=8)
    w, h = _jpeg_size(result)
    assert h == 8
    assert w == 4  # aspect ratio preserved: 16/32 → 4/8


def test_from_decoded_message__resize_both() -> None:
    message = SimpleNamespace(data=_h264_keyframe(width=16, height=16), format="h264")
    result = compressed_video.from_decoded_message(message, width=8, height=8)
    assert _jpeg_size(result) == (8, 8)


def test_from_decoded_message__missing_data_field() -> None:
    message = SimpleNamespace(format="h264")
    with pytest.raises(McapAccessError, match="has no field"):
        compressed_video.from_decoded_message(message)


def test_from_decoded_message__missing_format_field() -> None:
    message = SimpleNamespace(data=_h264_keyframe())
    with pytest.raises(McapAccessError, match="has no field"):
        compressed_video.from_decoded_message(message)


def test_from_decoded_message__non_bytes_data() -> None:
    message = SimpleNamespace(data="not bytes", format="h264")
    with pytest.raises(McapAccessError, match="non-byte"):
        compressed_video.from_decoded_message(message)


def test_from_decoded_message__non_string_format() -> None:
    message = SimpleNamespace(data=_h264_keyframe(), format=264)
    with pytest.raises(McapAccessError, match="non-string"):
        compressed_video.from_decoded_message(message)


def test_from_decoded_message__unsupported_format() -> None:
    message = SimpleNamespace(data=_h264_keyframe(), format="vp9")
    with pytest.raises(McapAccessError, match="Unsupported compressed video format"):
        compressed_video.from_decoded_message(message)


def test_from_decoded_message__undecodable_payload() -> None:
    message = SimpleNamespace(data=b"\x00\x00\x00\x01\x65\x00\x01\x02", format="h264")
    with pytest.raises(McapAccessError):
        compressed_video.from_decoded_message(message)


def test_codec_name__h264_variants() -> None:
    for fmt in ("h264", "H264", "avc"):
        assert compressed_video._codec_name(fmt) == "h264"


def test_codec_name__h265_variants() -> None:
    for fmt in ("h265", "H265", "hevc", "HEVC"):
        assert compressed_video._codec_name(fmt) == "hevc"


def test_codec_name__unsupported() -> None:
    with pytest.raises(McapAccessError, match="Unsupported compressed video format"):
        compressed_video._codec_name("vp9")
