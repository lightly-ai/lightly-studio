"""Deterministic requirement checks for egocentric video datasets."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import fsspec
from av import container

from lightly_studio.dataset.whisper_transcript import TimedTranscriptCaption

MIN_RESOLUTION_SHORT_EDGE_PX = 1080
MIN_RESOLUTION_LONG_EDGE_PX = 1920
MIN_VIDEO_DURATION_S = 60.0
MAX_VIDEO_DURATION_S = 20.0 * 60.0
MIN_DATASET_AVERAGE_DURATION_S = 60.0
MAX_DATASET_AVERAGE_DURATION_S = 5.0 * 60.0
MIN_ENGLISH_VIDEO_RATIO = 0.5
MAX_STATIC_CAMERA_RATIO_FOR_MINORITY = 0.5
PREFERRED_VIDEO_SUFFIX = ".mp4"


@dataclass(frozen=True)
class DatasetVideoQa:
    """Inputs needed to calculate dataset-level requirements."""

    duration_s: float | None
    language: str | None
    is_static_camera: bool


@dataclass(frozen=True)
class DatasetQaSummary:
    """Dataset-level duration, language, and static-camera results."""

    video_count: int
    average_duration_s: float | None
    average_duration_pass: bool
    english_video_count: int
    english_video_ratio: float
    english_video_ratio_pass: bool
    static_camera_count: int
    static_camera_ratio: float
    static_camera_minority_pass: bool


def has_minimum_1080p_resolution(width: int, height: int) -> bool:
    """Return whether landscape or portrait dimensions meet 1080p."""
    short_edge, long_edge = sorted((width, height))
    return short_edge >= MIN_RESOLUTION_SHORT_EDGE_PX and long_edge >= MIN_RESOLUTION_LONG_EDGE_PX


def has_valid_duration(duration_s: float | None) -> bool:
    """Return whether a video duration is within the required 1--20 minutes."""
    return (
        duration_s is not None
        and math.isfinite(duration_s)
        and MIN_VIDEO_DURATION_S <= duration_s <= MAX_VIDEO_DURATION_S
    )


def get_orientation(width: int, height: int) -> str:
    """Return a human-readable video orientation."""
    if width > height:
        return "landscape"
    if height > width:
        return "portrait"
    return "square"


def has_audio_stream(video_path: str) -> bool:
    """Return whether a video container declares at least one audio stream."""
    filesystem, filesystem_path = fsspec.core.url_to_fs(url=video_path)
    with filesystem.open(path=filesystem_path, mode="rb") as video_file:
        video_container = container.open(file=video_file)
        try:
            return bool(video_container.streams.audio)
        finally:
            video_container.close()


def has_preferred_video_format(video_path: str) -> bool:
    """Return whether a video uses the preferred MP4 container suffix."""
    return Path(video_path).suffix.lower() == PREFERRED_VIDEO_SUFFIX


def has_valid_caption_timestamps(
    captions: Sequence[TimedTranscriptCaption],
    duration_s: float | None,
) -> bool:
    """Validate final caption timestamp ordering and video bounds.

    Overlap is accepted because padded action-phrase windows can intentionally
    overlap. At least one timestamped caption is required.
    """
    if not captions or duration_s is None or not math.isfinite(duration_s):
        return False
    previous_start_s = -math.inf
    for caption in captions:
        if not _is_valid_caption_timestamp(
            caption=caption,
            duration_s=duration_s,
            previous_start_s=previous_start_s,
        ):
            return False
        previous_start_s = caption.start_time_s
    return True


def summarize_dataset(records: Sequence[DatasetVideoQa]) -> DatasetQaSummary:
    """Calculate directly testable dataset-level requirement results."""
    video_count = len(records)
    durations = [record.duration_s for record in records if record.duration_s is not None]
    average_duration_s = sum(durations) / len(durations) if durations else None
    all_durations_known = len(durations) == video_count
    average_duration_pass = (
        all_durations_known
        and average_duration_s is not None
        and MIN_DATASET_AVERAGE_DURATION_S <= average_duration_s <= MAX_DATASET_AVERAGE_DURATION_S
    )
    english_video_count = sum(is_english(language=record.language) for record in records)
    static_camera_count = sum(record.is_static_camera for record in records)
    english_ratio = english_video_count / video_count if video_count else 0.0
    static_ratio = static_camera_count / video_count if video_count else 0.0
    return DatasetQaSummary(
        video_count=video_count,
        average_duration_s=average_duration_s,
        average_duration_pass=average_duration_pass,
        english_video_count=english_video_count,
        english_video_ratio=english_ratio,
        english_video_ratio_pass=(video_count > 0 and english_ratio >= MIN_ENGLISH_VIDEO_RATIO),
        static_camera_count=static_camera_count,
        static_camera_ratio=static_ratio,
        static_camera_minority_pass=(
            video_count > 0 and static_ratio < MAX_STATIC_CAMERA_RATIO_FOR_MINORITY
        ),
    )


def is_english(language: str | None) -> bool:
    """Return whether a detected language code represents English."""
    if language is None:
        return False
    normalized = language.strip().lower().replace("_", "-")
    return normalized == "en" or normalized.startswith("en-")


def _is_valid_caption_timestamp(
    caption: TimedTranscriptCaption,
    duration_s: float,
    previous_start_s: float,
) -> bool:
    timestamps = (caption.start_time_s, caption.end_time_s)
    return (
        all(math.isfinite(timestamp) for timestamp in timestamps)
        and 0.0 <= caption.start_time_s < caption.end_time_s <= duration_s
        and caption.start_time_s >= previous_start_s
    )


__all__ = [
    "MAX_DATASET_AVERAGE_DURATION_S",
    "MAX_STATIC_CAMERA_RATIO_FOR_MINORITY",
    "MAX_VIDEO_DURATION_S",
    "MIN_DATASET_AVERAGE_DURATION_S",
    "MIN_ENGLISH_VIDEO_RATIO",
    "MIN_RESOLUTION_LONG_EDGE_PX",
    "MIN_RESOLUTION_SHORT_EDGE_PX",
    "MIN_VIDEO_DURATION_S",
    "DatasetQaSummary",
    "DatasetVideoQa",
    "get_orientation",
    "has_audio_stream",
    "has_minimum_1080p_resolution",
    "has_preferred_video_format",
    "has_valid_caption_timestamps",
    "has_valid_duration",
    "is_english",
    "summarize_dataset",
]
