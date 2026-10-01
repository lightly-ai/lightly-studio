"""Shared format constants for compressed video messages."""

from __future__ import annotations

H264_FORMATS: frozenset[str] = frozenset({"h264", "avc", "avc1"})
H265_FORMATS: frozenset[str] = frozenset({"h265", "hevc", "hvc1"})

DATA_FIELDS: tuple[str, ...] = ("data",)
FORMAT_FIELDS: tuple[str, ...] = ("format",)


def normalize_format(video_format: str) -> str:
    """Returns the video format in lower case and without surrounding whitespace."""
    return video_format.strip().lower()
