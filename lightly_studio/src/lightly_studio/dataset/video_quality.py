"""Compute and store automated video quality screening scores.

Scores classical CV signals on a uniform subsample of frames and writes video-level
aggregates as sample metadata. Intended for screening motion blur, poor lighting,
static cameras, and camera shake - the same metadata + filter pattern as
caption-segment match scoring.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any
from uuid import UUID

import cv2
import numpy as np
from av.container import InputContainer
from numpy.typing import NDArray
from sqlmodel import Session
from tqdm import tqdm

from lightly_studio.core.file_outcome_report import (
    BrokenInputFileError,
    MissingInputFileError,
)
from lightly_studio.dataset.video_frame_io import (
    DEFAULT_VIDEO_CHANNEL,
    OpenedVideo,
    open_video_container,
)
from lightly_studio.resolvers import metadata_resolver, video_resolver
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

logger = logging.getLogger(__name__)

DEFAULT_NUM_FRAMES = 8
DEFAULT_MAX_EDGE = 512
# Dense short bursts catch high-frequency handheld shake; sparse whole-video
# samples confuse scene changes with shake.
DEFAULT_SHAKE_BURSTS = 3
DEFAULT_SHAKE_FRAMES_PER_BURST = 20

# Metadata keys written on video samples.
BLUR_SCORE_KEY = "blur_score"
BRIGHTNESS_MEAN_KEY = "brightness_mean"
UNDEREXPOSURE_RATIO_KEY = "underexposure_ratio"
OVEREXPOSURE_RATIO_KEY = "overexposure_ratio"
LIGHTING_SCORE_KEY = "lighting_score"
MOTION_SCORE_KEY = "motion_score"
SHAKE_SCORE_KEY = "shake_score"

# Default screening thresholds.
# Higher blur/lighting is better; higher motion means less static; higher shake is worse.
DEFAULT_BLUR_SCORE_LOW_MAX = 50.0
DEFAULT_LIGHTING_SCORE_LOW_MAX = 0.45
DEFAULT_MOTION_SCORE_LOW_MAX = 3.0
DEFAULT_SHAKE_SCORE_HIGH_MIN = 4.0

_UNDEREXPOSURE_PIXEL_MAX = 20
_OVEREXPOSURE_PIXEL_MIN = 235
_MIN_FRAMES_FOR_SHAKE = 3
_MIN_TRACKED_POINTS = 8
_MAX_CORNERS = 200
_PHASE_CORRELATE_MIN_RESPONSE = 0.05


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

    shake_score: float
    """Mean camera-path acceleration in pixels/step^2 (higher = shakier)."""


@dataclass(frozen=True)
class ShakeSamplingConfig:
    """Dense-burst sampling parameters for camera-shake scoring."""

    num_bursts: int = DEFAULT_SHAKE_BURSTS
    frames_per_burst: int = DEFAULT_SHAKE_FRAMES_PER_BURST


def score_video_quality(
    video_path: str,
    *,
    num_frames: int = DEFAULT_NUM_FRAMES,
    max_edge: int = DEFAULT_MAX_EDGE,
    shake_sampling: ShakeSamplingConfig | None = None,
) -> VideoQualityScores:
    """Score blur, lighting, motion, and camera shake for a single video file.

    Opens ``video_path`` once. Blur/lighting/motion use ``num_frames`` uniformly
    spaced samples. Shake uses short dense bursts (near-consecutive frames) so
    high-frequency handheld jitter is not confused with scene changes.

    Args:
        video_path: Local path or fsspec URL of the video.
        num_frames: Number of uniformly spaced frames for blur/lighting/motion.
        max_edge: Max longest-edge length after resize. Must be >= 1.
        shake_sampling: Dense-burst sampling config for shake. Uses defaults when omitted.

    Returns:
        Aggregated ``VideoQualityScores``.

    Raises:
        ValueError: If sampling parameters are invalid.
        MissingInputFileError: If the video path does not resolve.
        BrokenInputFileError: If the video cannot be decoded.
    """
    _validate_quality_sampling_args(
        num_frames=num_frames,
        max_edge=max_edge,
        shake_sampling=shake_sampling or ShakeSamplingConfig(),
    )
    with open_video_container(video_path) as opened:
        return score_opened_video_quality(
            opened=opened,
            num_frames=num_frames,
            max_edge=max_edge,
            shake_sampling=shake_sampling,
        )


def score_opened_video_quality(
    opened: OpenedVideo,
    *,
    num_frames: int = DEFAULT_NUM_FRAMES,
    max_edge: int = DEFAULT_MAX_EDGE,
    shake_sampling: ShakeSamplingConfig | None = None,
) -> VideoQualityScores:
    """Score quality metrics from an already-open video container.

    Args:
        opened: Video opened via ``open_video_container``.
        num_frames: Number of uniformly spaced frames for blur/lighting/motion.
        max_edge: Max longest-edge length after resize. Must be >= 1.
        shake_sampling: Dense-burst sampling config for shake. Uses defaults when omitted.

    Returns:
        Aggregated ``VideoQualityScores``.

    Raises:
        ValueError: If sampling parameters are invalid.
        BrokenInputFileError: If frames cannot be decoded.
    """
    shake_cfg = shake_sampling or ShakeSamplingConfig()
    _validate_quality_sampling_args(
        num_frames=num_frames,
        max_edge=max_edge,
        shake_sampling=shake_cfg,
    )
    quality_frames, bursts = _sample_quality_and_shake_frames_from_opened(
        opened=opened,
        num_frames=num_frames,
        max_edge=max_edge,
        shake_sampling=shake_cfg,
    )
    scores = aggregate_frame_quality(quality_frames)
    return replace(scores, shake_score=camera_shake_score_from_bursts(bursts))


def _validate_quality_sampling_args(
    *,
    num_frames: int,
    max_edge: int,
    shake_sampling: ShakeSamplingConfig,
) -> None:
    if num_frames < 1:
        raise ValueError(f"num_frames must be >= 1, got {num_frames}.")
    if max_edge < 1:
        raise ValueError(f"max_edge must be >= 1, got {max_edge}.")
    if shake_sampling.num_bursts < 1:
        raise ValueError(f"shake_bursts must be >= 1, got {shake_sampling.num_bursts}.")
    if shake_sampling.frames_per_burst < _MIN_FRAMES_FOR_SHAKE:
        raise ValueError(
            f"shake_frames_per_burst must be >= {_MIN_FRAMES_FOR_SHAKE}, "
            f"got {shake_sampling.frames_per_burst}."
        )


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
        # Placeholder; ``score_video_quality`` overwrites with dense-burst shake.
        shake_score=camera_shake_score(frames),
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


def estimate_global_translation(
    prev: NDArray[np.uint8],
    curr: NDArray[np.uint8],
) -> tuple[float, float]:
    """Estimate global (dx, dy) translation from ``prev`` to ``curr``.

    Prefers sparse Lucas-Kanade tracking (works on soft/blurry handheld footage).
    Falls back to phase correlation when too few points are tracked.
    """
    points = cv2.goodFeaturesToTrack(
        prev,
        maxCorners=_MAX_CORNERS,
        qualityLevel=0.01,
        minDistance=8,
        blockSize=7,
    )
    if points is not None and len(points) >= _MIN_TRACKED_POINTS:
        next_points, status, _err = cv2.calcOpticalFlowPyrLK(prev, curr, points, None)
        if next_points is not None and status is not None:
            ok = status.reshape(-1) == 1
            if int(np.count_nonzero(ok)) >= _MIN_TRACKED_POINTS:
                deltas = next_points[ok].reshape(-1, 2) - points[ok].reshape(-1, 2)
                return float(np.median(deltas[:, 0])), float(np.median(deltas[:, 1]))

    (dx, dy), response = cv2.phaseCorrelate(np.float32(prev), np.float32(curr))
    if response < _PHASE_CORRELATE_MIN_RESPONSE:
        return 0.0, 0.0
    return float(dx), float(dy)


def camera_shake_score(frames: Sequence[NDArray[np.uint8]]) -> float:
    """Score camera shake as mean acceleration of the global translation path.

    Steady pans keep nearly-constant frame-to-frame deltas (acceleration ~0).
    Handheld shake changes direction/speed rapidly, so second differences are large.
    Returns 0.0 when fewer than three frames are available.
    """
    if len(frames) < _MIN_FRAMES_FOR_SHAKE:
        return 0.0

    deltas = np.asarray(
        [estimate_global_translation(frames[i], frames[i + 1]) for i in range(len(frames) - 1)],
        dtype=np.float64,
    )
    if len(deltas) < 2:  # noqa: PLR2004
        return 0.0

    acceleration = np.diff(deltas, axis=0)
    return float(np.mean(np.linalg.norm(acceleration, axis=1)))


def camera_shake_score_from_bursts(bursts: Sequence[Sequence[NDArray[np.uint8]]]) -> float:
    """Aggregate per-burst shake scores, taking the max (worst window)."""
    scores = [
        camera_shake_score(burst) for burst in bursts if len(burst) >= _MIN_FRAMES_FOR_SHAKE
    ]
    if not scores:
        return 0.0
    return float(max(scores))


def scores_to_metadata(scores: VideoQualityScores) -> dict[str, float]:
    """Convert scores to the metadata key/value mapping written on samples."""
    return {
        BLUR_SCORE_KEY: scores.blur_score,
        BRIGHTNESS_MEAN_KEY: scores.brightness_mean,
        UNDEREXPOSURE_RATIO_KEY: scores.underexposure_ratio,
        OVEREXPOSURE_RATIO_KEY: scores.overexposure_ratio,
        LIGHTING_SCORE_KEY: scores.lighting_score,
        MOTION_SCORE_KEY: scores.motion_score,
        SHAKE_SCORE_KEY: scores.shake_score,
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
        num_frames: Frames sampled per video for blur/lighting/motion.
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


def _sample_quality_and_shake_frames_from_opened(
    opened: OpenedVideo,
    num_frames: int,
    max_edge: int,
    shake_sampling: ShakeSamplingConfig,
) -> tuple[list[NDArray[np.uint8]], list[list[NDArray[np.uint8]]]]:
    """Sample quality frames plus dense shake bursts from an open container."""
    quality_frames = _decode_frames_at_timestamps(
        video_container=opened.container,
        filepath=opened.filepath,
        time_base=opened.time_base,
        timestamps_s=np.linspace(
            0.0,
            opened.duration_s,
            num=num_frames,
            endpoint=False,
            dtype=np.float64,
        ).tolist(),
        max_edge=max_edge,
    )
    bursts = _decode_shake_bursts(
        video_container=opened.container,
        filepath=opened.filepath,
        time_base=opened.time_base,
        duration_seconds=opened.duration_s,
        shake_sampling=shake_sampling,
        max_edge=max_edge,
    )
    return quality_frames, bursts


def _decode_shake_bursts(  # noqa: PLR0913
    video_container: InputContainer,
    filepath: str,
    time_base: float,
    duration_seconds: float,
    shake_sampling: ShakeSamplingConfig,
    max_edge: int,
) -> list[list[NDArray[np.uint8]]]:
    """Decode short runs of consecutive frames for shake analysis.

    Seeks once to each burst start, then decodes forward without further seeks so
    neighboring samples are true consecutive frames (seek-per-timestamp often snaps
    to the same keyframe and collapses the motion signal).
    """
    frames_per_burst = shake_sampling.frames_per_burst
    # Estimate burst length in seconds from stream FPS when available.
    video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
    average_rate = video_stream.average_rate
    fps = float(average_rate) if average_rate is not None and float(average_rate) > 0 else 15.0
    burst_span_s = (frames_per_burst - 1) / fps

    if duration_seconds <= burst_span_s:
        starts = [0.0]
    else:
        starts = np.linspace(
            0.0,
            max(duration_seconds - burst_span_s, 0.0),
            num=shake_sampling.num_bursts,
            endpoint=True,
            dtype=np.float64,
        ).tolist()

    bursts: list[list[NDArray[np.uint8]]] = []
    for start_s in starts:
        bursts.append(
            _decode_consecutive_frames(
                video_container=video_container,
                filepath=filepath,
                time_base=time_base,
                start_s=start_s,
                num_frames=frames_per_burst,
                max_edge=max_edge,
            )
        )
    return bursts

def _decode_consecutive_frames(  # noqa: PLR0913
    video_container: InputContainer,
    filepath: str,
    time_base: float,
    start_s: float,
    num_frames: int,
    max_edge: int,
    video_channel: int = DEFAULT_VIDEO_CHANNEL,
) -> list[NDArray[np.uint8]]:
    """Seek to ``start_s``, then decode ``num_frames`` consecutive frames."""
    video_stream = video_container.streams.video[video_channel]
    pts_target = int(start_s / time_base)
    video_container.seek(offset=pts_target, stream=video_stream)

    frames: list[NDArray[np.uint8]] = []
    try:
        for frame in video_container.decode(video=video_channel):
            rgb = np.asarray(frame.to_ndarray(format="rgb24"), dtype=np.uint8)
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            frames.append(_resize_max_edge(gray, max_edge=max_edge))
            if len(frames) >= num_frames:
                break
    except StopIteration:
        pass

    if len(frames) < _MIN_FRAMES_FOR_SHAKE:
        raise BrokenInputFileError(
            f"Unable to decode shake burst at {start_s:.3f}s from video '{filepath}'."
        )
    return frames


def _decode_frames_at_timestamps(
    video_container: InputContainer,
    filepath: str,
    time_base: float,
    timestamps_s: Sequence[float],
    max_edge: int,
) -> list[NDArray[np.uint8]]:
    video_stream = video_container.streams.video[DEFAULT_VIDEO_CHANNEL]
    frames: list[NDArray[np.uint8]] = []
    for ts_target in timestamps_s:
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
    "DEFAULT_SHAKE_BURSTS",
    "DEFAULT_SHAKE_FRAMES_PER_BURST",
    "DEFAULT_SHAKE_SCORE_HIGH_MIN",
    "LIGHTING_SCORE_KEY",
    "MOTION_SCORE_KEY",
    "OVEREXPOSURE_RATIO_KEY",
    "SHAKE_SCORE_KEY",
    "UNDEREXPOSURE_RATIO_KEY",
    "ShakeSamplingConfig",
    "VideoQualityScores",
    "aggregate_frame_quality",
    "camera_shake_score",
    "camera_shake_score_from_bursts",
    "compute_and_store_quality_metadata",
    "estimate_global_translation",
    "inter_frame_motion_score",
    "laplacian_variance",
    "lighting_score",
    "overexposure_ratio",
    "score_opened_video_quality",
    "score_video_quality",
    "scores_to_metadata",
    "set_video_quality_metadata",
    "underexposure_ratio",
]
