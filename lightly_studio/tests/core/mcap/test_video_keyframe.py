from __future__ import annotations

from types import SimpleNamespace

import pytest

from lightly_studio.core.mcap import video_keyframe


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


def test_is_keyframe_message() -> None:
    message = SimpleNamespace(data=h265_keyframe(), format="h265")
    assert video_keyframe.is_keyframe_message(message)


def test_is_keyframe_message__delta_frame() -> None:
    message = SimpleNamespace(data=h265_delta_frame(), format="h265")
    assert not video_keyframe.is_keyframe_message(message)


def test_is_keyframe_message__dict() -> None:
    message = {"data": h264_keyframe(), "format": "h264"}
    assert video_keyframe.is_keyframe_message(message)


def test_is_keyframe_message__unsupported_format() -> None:
    message = SimpleNamespace(data=h265_keyframe(), format="vp9")
    assert not video_keyframe.is_keyframe_message(message)


def test_is_keyframe_message__no_payload() -> None:
    message = SimpleNamespace(format="h265")
    assert not video_keyframe.is_keyframe_message(message)


@pytest.mark.parametrize(
    ("video_format", "expected"),
    [("h265", True), ("HEVC", True), ("h264", True), ("vp9", False), ("av1", False)],
)
def test_is_format_supported(video_format: str, expected: bool) -> None:
    assert video_keyframe.is_format_supported(video_format) == expected


def test_is_keyframe__h265() -> None:
    assert video_keyframe.is_keyframe(data=h265_keyframe(), video_format="h265")
    assert not video_keyframe.is_keyframe(data=h265_delta_frame(), video_format="h265")


def test_is_keyframe__h265_after_parameter_sets() -> None:
    # A keyframe is commonly preceded by the VPS, SPS, and PPS NAL units.
    video_parameter_set = b"\x00\x00\x00\x01\x40\x01\x0c"
    sequence_parameter_set = b"\x00\x00\x00\x01\x42\x01\x01"
    data = video_parameter_set + sequence_parameter_set + h265_keyframe()
    assert video_keyframe.is_keyframe(data=data, video_format="h265")


def test_is_keyframe__h265_three_byte_start_code() -> None:
    data = b"\x00\x00\x01\x26\x01\x00\x01"
    assert video_keyframe.is_keyframe(data=data, video_format="h265")


def test_is_keyframe__h264() -> None:
    assert video_keyframe.is_keyframe(data=h264_keyframe(), video_format="h264")
    assert not video_keyframe.is_keyframe(data=h264_delta_frame(), video_format="h264")


def test_is_keyframe__no_start_code() -> None:
    assert not video_keyframe.is_keyframe(data=b"\x26\x01\x00\x01", video_format="h265")


def test_is_keyframe__empty_payload() -> None:
    assert not video_keyframe.is_keyframe(data=b"", video_format="h265")


def test_is_keyframe__truncated_after_start_code() -> None:
    assert not video_keyframe.is_keyframe(data=b"\x00\x00\x00\x01", video_format="h265")


def test_is_keyframe__unsupported_format() -> None:
    with pytest.raises(ValueError, match=r"Cannot detect keyframes in video format 'vp9'\."):
        video_keyframe.is_keyframe(data=h265_keyframe(), video_format="vp9")
