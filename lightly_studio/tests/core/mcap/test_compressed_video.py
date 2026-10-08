"""Tests for compressed_video.py — decoding CompressedVideo messages to JPEG."""

from __future__ import annotations

import io
from types import SimpleNamespace

import av
import pytest
from av import VideoStream
from PIL import Image

from lightly_studio.core.mcap import compressed_video
from lightly_studio.core.mcap.compressed_video import VideoDecoder
from lightly_studio.core.mcap.errors import McapAccessError
from tests.core.mcap import helpers


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


class TestVideoDecoder:
    @pytest.mark.parametrize(
        ("keyframe_log_time_ns", "log_time_ns", "expected"),
        [
            (100, 200, True),  # A later frame of the same GOP.
            (100, 150, True),  # The last decoded frame again.
            (100, 120, False),  # An earlier frame.
            (300, 400, False),  # A frame of another GOP.
        ],
    )
    def test_can_continue_to(
        self, keyframe_log_time_ns: int, log_time_ns: int, expected: bool
    ) -> None:
        keyframe, delta_frame = helpers.h264_access_units(gray_levels=[0, 255])
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        decoder.decode(
            decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=100
        )
        decoder.decode(
            decoded_message=SimpleNamespace(data=delta_frame, format="h264"), log_time_ns=150
        )

        assert (
            decoder.can_continue_to(
                keyframe_log_time_ns=keyframe_log_time_ns, log_time_ns=log_time_ns
            )
            is expected
        )

    def test_can_continue_to__new_decoder(self) -> None:
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        assert not decoder.can_continue_to(keyframe_log_time_ns=100, log_time_ns=100)

    def test_decode__steps_forward(self) -> None:
        keyframe, delta_frame = helpers.h264_access_units(gray_levels=[0, 255])
        decoder = VideoDecoder(keyframe_log_time_ns=100)

        decoder.decode(
            decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=100
        )
        keyframe_picture = decoder.frame(log_time_ns=100)
        assert keyframe_picture is not None
        keyframe_jpeg = compressed_video.to_jpeg(frame=keyframe_picture)
        decoder.decode(
            decoded_message=SimpleNamespace(data=delta_frame, format="h264"), log_time_ns=200
        )
        delta_frame_picture = decoder.frame(log_time_ns=200)
        assert delta_frame_picture is not None
        delta_frame_jpeg = compressed_video.to_jpeg(frame=delta_frame_picture)

        assert helpers.jpeg_mean_gray_level(keyframe_jpeg) < 32
        assert helpers.jpeg_mean_gray_level(delta_frame_jpeg) > 223
        assert decoder.last_log_time_ns == 200
        assert decoder.can_continue_to(keyframe_log_time_ns=100, log_time_ns=300)

    def test_decode__non_bytes_data(self) -> None:
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        with pytest.raises(McapAccessError, match="non-byte"):
            decoder.decode(
                decoded_message=SimpleNamespace(data="not bytes", format="h264"), log_time_ns=100
            )

    def test_decode__undecodable_payload(self) -> None:
        (keyframe,) = helpers.h264_access_units(gray_levels=[0])
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        decoder.decode(
            decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=100
        )

        with pytest.raises(McapAccessError, match="could not decode"):
            decoder.decode(
                decoded_message=SimpleNamespace(
                    data=b"\x00\x00\x00\x01\x65\x00\x01\x02", format="h264"
                ),
                log_time_ns=200,
            )

        assert decoder.last_log_time_ns == 100
        assert not decoder.can_continue_to(keyframe_log_time_ns=100, log_time_ns=300)
        with pytest.raises(ValueError, match="flushed"):
            decoder.decode(
                decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=300
            )

    def test_decode__after_flush(self) -> None:
        (keyframe,) = helpers.h264_access_units(gray_levels=[0])
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        decoder.flush()

        with pytest.raises(ValueError, match="flushed"):
            decoder.decode(
                decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=100
            )

    @pytest.mark.parametrize("log_time_ns", [100, 50])
    def test_decode__log_time_not_later(self, log_time_ns: int) -> None:
        keyframe, delta_frame = helpers.h264_access_units(gray_levels=[0, 255])
        decoder = VideoDecoder(keyframe_log_time_ns=100)
        decoder.decode(
            decoded_message=SimpleNamespace(data=keyframe, format="h264"), log_time_ns=100
        )

        with pytest.raises(ValueError, match="must be later"):
            decoder.decode(
                decoded_message=SimpleNamespace(data=delta_frame, format="h264"),
                log_time_ns=log_time_ns,
            )


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
