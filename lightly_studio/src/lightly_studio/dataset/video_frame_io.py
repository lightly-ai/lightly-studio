"""Shared helpers for opening videos once and seeking frames via fsspec + PyAV."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import fsspec
from av import FFmpegError, container
from av.container import InputContainer

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    MissingInputFileError,
)

DEFAULT_VIDEO_CHANNEL = 0


@dataclass(frozen=True)
class OpenedVideo:
    """An opened video container with resolved timing metadata."""

    container: InputContainer
    time_base: float
    duration_s: float
    filepath: str


@contextmanager
def open_video_container(filepath: str) -> Iterator[OpenedVideo]:
    """Open a local or remote video once and yield timing metadata.

    Args:
        filepath: Local path or fsspec URL of the video.

    Yields:
        ``OpenedVideo`` with an open PyAV container. The container is closed when
        the context exits.

    Raises:
        MissingInputFileError: If the path does not resolve.
        BrokenInputFileError: If the video cannot be opened or has no usable duration.
    """
    fs, fs_path = fsspec.core.url_to_fs(url=filepath)
    if not fs.exists(fs_path):
        raise MissingInputFileError(f"Video does not exist: '{filepath}'.")

    try:
        with (
            fs.open(path=fs_path, mode="rb") as video_file,
            container.open(file=video_file) as video_container,
        ):
            time_base, duration_s = _video_timing(
                video_container=video_container,
                filepath=filepath,
            )
            yield OpenedVideo(
                container=video_container,
                time_base=time_base,
                duration_s=duration_s,
                filepath=filepath,
            )
    except (OSError, FFmpegError, IndexError) as error:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.") from error


def _video_timing(video_container: InputContainer, *, filepath: str) -> tuple[float, float]:
    """Return ``(time_base, duration_s)`` for the default video stream."""
    video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
    duration_pts = video_stream.duration
    raw_time_base = video_stream.time_base
    if duration_pts is None or duration_pts <= 0 or raw_time_base is None:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.")
    time_base = float(raw_time_base)
    if time_base <= 0.0:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.")
    return time_base, duration_pts * time_base
