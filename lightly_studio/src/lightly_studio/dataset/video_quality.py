"""Compute and store automated video quality screening scores.

Scores classical CV signals on a uniform subsample of frames and writes video-level
aggregates as sample metadata. Intended for screening motion blur, poor lighting, and
(optionally) static cameras — the same metadata + filter pattern as caption-segment
match scoring.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import cv2
import fsspec
import numpy as np
from av import FFmpegError, container
from av.container import InputContainer
from numpy.typing import NDArray
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    MissingInputFileError,
)
from lightly_studio.resolvers import metadata_resolver, video_resolver
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

logger = logging.getLogger(__name__)

DEFAULT_VIDEO_CHANNEL = 0
DEFAULT_NUM_FRAMES = 8
DEFAULT_MAX_EDGE = 512

# Metadata keys written on video samples.
BLUR_SCORE_KEY = "blur_score"
BRIGHTNESS_MEAN_KEY = "brightness_mean"
UNDEREXPOSURE_RATIO_KEY = "underexposure_ratio"
OVEREXPOSURE_RATIO_KEY = "overexposure_ratio"
LIGHTING_SCORE_KEY = "lighting_score"
MOTION_SCORE_KEY = "motion_score"

# Default screening thresholds (higher blur/lighting/motion is better).
DEFAULT_BLUR_SCORE_LOW_MAX = 50.0
DEFAULT_LIGHTING_SCORE_LOW_MAX = 0.45
DEFAULT_MOTION_SCORE_LOW_MAX = 3.0

_UNDEREXPOSURE_PIXEL_MAX = 20
_OVEREXPOSURE_PIXEL_MIN = 235


@dataclass(frozen=True)
class VideoQualityScores:
    """Video-level quality aggregates from subsampled frames."""

    blur_score: float
    """P10 of per-frame Laplacian variance (higher = sharper)."""

    brightness_mean: float
    """Mean grayscale luminance in ``[0, 255]``."""

    underexposure_ratio: float
    """Fraction of pixels darker than near-black."""

    overexposure_ratio: float
    """Fraction of pixels brighter than near-white."""

    lighting_score: float
    """Combined lighting quality in ``[0, 1]`` (higher = better)."""

    motion_score: float
    """Mean absolute inter-frame difference (higher = more motion)."""


def score_video_quality(
    video_path: str,
    *,
    num_frames: int = DEFAULT_NUM_FRAMES,
    max_edge: int = DEFAULT_MAX_EDGE,
) -> VideoQualityScores:
    """Score blur, lighting, and motion for a single video file.

    Opens ``video_path`` once, samples ``num_frames`` uniformly, resizes so the
    longest edge is at most ``max_edge`` (for resolution-stable metrics), and
    aggregates per-frame signals.

    Args:
        video_path: Local path or fsspec URL of the video.
        num_frames: Number of uniformly spaced frames to sample. Must be >= 1.
        max_edge: Max longest-edge length after resize. Must be >= 1.

    Returns:
        Aggregated ``VideoQualityScores``.

    Raises:
        ValueError: If ``num_frames`` or ``max_edge`` is invalid.
        MissingInputFileError: If the video path does not resolve.
        BrokenInputFileError: If the video cannot be decoded.
    """
    if num_frames < 1:
        raise ValueError(f"num_frames must be >= 1, got {num_frames}.")
    if max_edge < 1:
        raise ValueError(f"max_edge must be >= 1, got {max_edge}.")

    frames = _sample_grayscale_frames(
        filepath=video_path,
        num_frames=num_frames,
        max_edge=max_edge,
    )
    return aggregate_frame_quality(frames)


def aggregate_frame_quality(frames: Sequence[NDArray[np.uint8]]) -> VideoQualityScores:
    """Aggregate per-frame quality metrics into video-level scores.

    Args:
        frames: Grayscale ``uint8`` frames of equal spatial size. Must be non-empty.

    Returns:
        Aggregated ``VideoQualityScores``.

    Raises:
        ValueError: If ``frames`` is empty.
    """
    if not frames:
        raise ValueError("frames must be non-empty.")

    blur_scores = [float(laplacian_variance(frame)) for frame in frames]
    brightness_means = [float(np.mean(frame)) for frame in frames]
    underexposure_ratios = [float(underexposure_ratio(frame)) for frame in frames]
    overexposure_ratios = [float(overexposure_ratio(frame)) for frame in frames]

    brightness_mean = float(np.mean(brightness_means))
    under_ratio = float(np.mean(underexposure_ratios))
    over_ratio = float(np.mean(overexposure_ratios))

    return VideoQualityScores(
        blur_score=float(np.percentile(blur_scores, 10)),
        brightness_mean=brightness_mean,
        underexposure_ratio=under_ratio,
        overexposure_ratio=over_ratio,
        lighting_score=lighting_score(
            brightness_mean=brightness_mean,
            underexposure_ratio=under_ratio,
            overexposure_ratio=over_ratio,
        ),
        motion_score=inter_frame_motion_score(frames),
    )


def laplacian_variance(gray: NDArray[np.uint8]) -> float:
    """Return Laplacian variance of a grayscale frame (higher = sharper)."""
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def underexposure_ratio(gray: NDArray[np.uint8]) -> float:
    """Return fraction of near-black pixels."""
    return float(np.mean(gray < _UNDEREXPOSURE_PIXEL_MAX))


def overexposure_ratio(gray: NDArray[np.uint8]) -> float:
    """Return fraction of near-white pixels."""
    return float(np.mean(gray > _OVEREXPOSURE_PIXEL_MIN))


def lighting_score(
    *,
    brightness_mean: float,
    underexposure_ratio: float,
    overexposure_ratio: float,
) -> float:
    """Combine mean luminance and clip ratios into a ``[0, 1]`` lighting quality.

    Higher is better (mid-range brightness and little clipping).
    """
    mid_quality = 1.0 - abs(brightness_mean - 127.5) / 127.5
    clip_quality = 1.0 - max(underexposure_ratio, overexposure_ratio)
    return float(min(mid_quality, clip_quality))


def inter_frame_motion_score(frames: Sequence[NDArray[np.uint8]]) -> float:
    """Mean absolute difference between consecutive grayscale frames.

    Returns 0.0 when fewer than two frames are provided.
    """
    if len(frames) < 2:  # noqa: PLR2004
        return 0.0
    diffs = [
        float(np.mean(np.abs(frames[i].astype(np.float32) - frames[i + 1].astype(np.float32))))
        for i in range(len(frames) - 1)
    ]
    return float(np.mean(diffs))


def scores_to_metadata(scores: VideoQualityScores) -> dict[str, float]:
    """Convert scores to the metadata key/value mapping written on samples."""
    return {
        BLUR_SCORE_KEY: scores.blur_score,
        BRIGHTNESS_MEAN_KEY: scores.brightness_mean,
        UNDEREXPOSURE_RATIO_KEY: scores.underexposure_ratio,
        OVEREXPOSURE_RATIO_KEY: scores.overexposure_ratio,
        LIGHTING_SCORE_KEY: scores.lighting_score,
        MOTION_SCORE_KEY: scores.motion_score,
    }


def set_video_quality_metadata(
    session: Session,
    video_sample_id: UUID,
    scores: VideoQualityScores,
) -> None:
    """Write quality score metadata onto a video sample."""
    metadata_resolver.bulk_update_metadata(
        session,
        [(video_sample_id, scores_to_metadata(scores))],
    )


def compute_and_store_quality_metadata(
    session: Session,
    collection_id: UUID,
    *,
    filters: VideoFilter | None = None,
    num_frames: int = DEFAULT_NUM_FRAMES,
    max_edge: int = DEFAULT_MAX_EDGE,
) -> int:
    """Score videos in a collection and store results as sample metadata.

    Args:
        session: Database session.
        collection_id: Video collection to process.
        filters: Optional video filter to restrict which samples are scored.
        num_frames: Frames sampled per video.
        max_edge: Max longest-edge length after resize.

    Returns:
        Number of videos successfully scored and stored.
    """
    result = video_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        filters=filters,
    )
    videos = list(result.samples)
    if not videos:
        return 0

    sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in tqdm(videos, desc="Scoring video quality", unit="video"):
        try:
            scores = score_video_quality(
                video.file_path_abs,
                num_frames=num_frames,
                max_edge=max_edge,
            )
        except (MissingInputFileError, BrokenInputFileError, ValueError, OSError) as error:
            logger.warning("Skipping video %s: %s", video.file_path_abs, error)
            continue
        sample_metadata.append((video.sample_id, scores_to_metadata(scores)))

    metadata_resolver.bulk_update_metadata(session, sample_metadata)
    return len(sample_metadata)


def _sample_grayscale_frames(
    filepath: str,
    num_frames: int,
    max_edge: int,
) -> list[NDArray[np.uint8]]:
    """Open a video once and return uniformly sampled resized grayscale frames."""
    fs, fs_path = fsspec.core.url_to_fs(url=filepath)
    if not fs.exists(fs_path):
        raise MissingInputFileError(f"Video does not exist: '{filepath}'.")

    try:
        with (
            fs.open(path=fs_path, mode="rb") as video_file,
            container.open(file=video_file) as video_container,
        ):
            return _decode_grayscale_frames(
                video_container=video_container,
                filepath=filepath,
                num_frames=num_frames,
                max_edge=max_edge,
            )
    except (OSError, FFmpegError, IndexError) as error:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.") from error


def _decode_grayscale_frames(
    video_container: InputContainer,
    filepath: str,
    num_frames: int,
    max_edge: int,
) -> list[NDArray[np.uint8]]:
    video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
    duration_pts = video_stream.duration
    raw_time_base = video_stream.time_base
    if duration_pts is None or duration_pts <= 0 or raw_time_base is None:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.")
    time_base = float(raw_time_base)
    if time_base <= 0.0:
        raise BrokenInputFileError(f"Unable to read frames from video '{filepath}'.")

    duration_seconds = duration_pts * time_base
    ts_to_sample = np.linspace(
        0.0,
        duration_seconds,
        num=num_frames,
        endpoint=False,
        dtype=np.float64,
    )

    frames: list[NDArray[np.uint8]] = []
    for ts_target in ts_to_sample:
        pts_target = int(ts_target / time_base)
        video_container.seek(offset=pts_target, stream=video_stream)
        try:
            frame = next(video_container.decode(video=DEFAULT_VIDEO_CHANNEL))
        except StopIteration as error:
            raise BrokenInputFileError(
                f"Unable to decode frame at {ts_target:.3f}s from video '{filepath}'."
            ) from error
        rgb = np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)
        gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
        frames.append(_resize_max_edge(gray, max_edge=max_edge))
    return frames


def _resize_max_edge(gray: NDArray[np.uint8], max_edge: int) -> NDArray[np.uint8]:
    height, width = gray.shape[:2]
    longest = max(height, width)
    if longest <= max_edge:
        return gray
    scale = max_edge / float(longest)
    new_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)


__all__ = [
    "BLUR_SCORE_KEY",
    "BRIGHTNESS_MEAN_KEY",
    "DEFAULT_BLUR_SCORE_LOW_MAX",
    "DEFAULT_LIGHTING_SCORE_LOW_MAX",
    "DEFAULT_MAX_EDGE",
    "DEFAULT_MOTION_SCORE_LOW_MAX",
    "DEFAULT_NUM_FRAMES",
    "LIGHTING_SCORE_KEY",
    "MOTION_SCORE_KEY",
    "OVEREXPOSURE_RATIO_KEY",
    "UNDEREXPOSURE_RATIO_KEY",
    "VideoQualityScores",
    "aggregate_frame_quality",
    "compute_and_store_quality_metadata",
    "inter_frame_motion_score",
    "laplacian_variance",
    "lighting_score",
    "overexposure_ratio",
    "score_video_quality",
    "scores_to_metadata",
    "set_video_quality_metadata",
    "underexposure_ratio",
]
