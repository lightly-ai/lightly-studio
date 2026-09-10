"""Unit tests for video quality screening scores."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from sqlmodel import Session

from lightly_studio.dataset import video_quality
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver, video_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video import helpers as video_helpers


def _checkerboard(size: int = 128, cell: int = 8) -> np.ndarray:
    """Sharp high-contrast grayscale pattern."""
    coords = np.arange(size) // cell
    grid = (coords[:, None] + coords[None, :]) % 2
    return (grid * 255).astype(np.uint8)


def _blurred_checkerboard(size: int = 128, cell: int = 8, ksize: int = 31) -> np.ndarray:
    sharp = _checkerboard(size=size, cell=cell)
    return cv2.GaussianBlur(sharp, (ksize, ksize), 0)


def test_laplacian_variance__sharp_higher_than_blurry() -> None:
    sharp = _checkerboard()
    blurry = _blurred_checkerboard()
    assert video_quality.laplacian_variance(sharp) > video_quality.laplacian_variance(blurry) * 5


def test_underexposure_and_overexposure_ratios() -> None:
    dark = np.full((32, 32), 5, dtype=np.uint8)
    bright = np.full((32, 32), 250, dtype=np.uint8)
    mid = np.full((32, 32), 128, dtype=np.uint8)

    assert video_quality.underexposure_ratio(dark) == pytest.approx(1.0)
    assert video_quality.overexposure_ratio(bright) == pytest.approx(1.0)
    assert video_quality.underexposure_ratio(mid) == pytest.approx(0.0)
    assert video_quality.overexposure_ratio(mid) == pytest.approx(0.0)


def test_lighting_score__mid_better_than_extreme() -> None:
    mid = video_quality.lighting_score(
        brightness_mean=128.0, underexposure_ratio=0.0, overexposure_ratio=0.0
    )
    dark = video_quality.lighting_score(
        brightness_mean=10.0, underexposure_ratio=0.9, overexposure_ratio=0.0
    )
    assert mid > dark


def test_inter_frame_motion_score__static_vs_moving() -> None:
    frame_a = _checkerboard()
    frame_b = np.roll(frame_a, shift=20, axis=1)
    static = video_quality.inter_frame_motion_score([frame_a, frame_a, frame_a])
    moving = video_quality.inter_frame_motion_score([frame_a, frame_b, frame_a])
    assert static == pytest.approx(0.0)
    assert moving > 10.0


def test_inter_frame_motion_score__single_frame() -> None:
    assert video_quality.inter_frame_motion_score([_checkerboard()]) == 0.0


def test_aggregate_frame_quality__empty_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        video_quality.aggregate_frame_quality([])


def test_aggregate_frame_quality__blurry_and_dark() -> None:
    frames = [_blurred_checkerboard() // 8 for _ in range(4)]
    scores = video_quality.aggregate_frame_quality(frames)
    assert (
        scores.blur_score
        < video_quality.aggregate_frame_quality([_checkerboard() for _ in range(4)]).blur_score
    )
    assert scores.brightness_mean < 50
    assert scores.lighting_score < 0.6


def test_score_video_quality__and_store_metadata(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_path = video_helpers.create_video_file(
        output_path=tmp_path / "solid.mp4",
        width=64,
        height=64,
        num_frames=16,
        fps=8,
    )
    video = video_helpers.create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path=str(video_path)),
    )

    scores = video_quality.score_video_quality(str(video_path), num_frames=4, max_edge=64)
    # Solid black frames: low blur, low brightness, low motion.
    assert scores.brightness_mean < 5
    assert scores.motion_score == pytest.approx(0.0, abs=1.0)
    assert scores.blur_score < video_quality.DEFAULT_BLUR_SCORE_LOW_MAX

    video_quality.set_video_quality_metadata(
        session=db_session, video_sample_id=video.sample_id, scores=scores
    )

    assert metadata_resolver.get_value_for_sample(
        session=db_session, sample_id=video.sample_id, key=video_quality.BLUR_SCORE_KEY
    ) == pytest.approx(scores.blur_score)
    assert metadata_resolver.get_value_for_sample(
        session=db_session, sample_id=video.sample_id, key=video_quality.LIGHTING_SCORE_KEY
    ) == pytest.approx(scores.lighting_score)
    assert metadata_resolver.get_value_for_sample(
        session=db_session, sample_id=video.sample_id, key=video_quality.MOTION_SCORE_KEY
    ) == pytest.approx(scores.motion_score)


def test_compute_and_store_quality_metadata(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_path = video_helpers.create_video_file(
        output_path=tmp_path / "clip.mp4",
        width=64,
        height=64,
        num_frames=12,
        fps=6,
    )
    video_helpers.create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=video_helpers.VideoStub(path=str(video_path)),
    )

    scored = video_quality.compute_and_store_quality_metadata(
        session=db_session,
        collection_id=collection.collection_id,
        num_frames=4,
        max_edge=64,
    )
    assert scored == 1

    result = video_resolver.get_all_by_collection_id(
        session=db_session, collection_id=collection.collection_id
    )
    assert len(result.samples) == 1
    stored = metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=result.samples[0].sample_id,
        key=video_quality.BLUR_SCORE_KEY,
    )
    assert isinstance(stored, float)


def test_score_video_quality__invalid_args() -> None:
    with pytest.raises(ValueError, match="num_frames"):
        video_quality.score_video_quality("unused.mp4", num_frames=0)
    with pytest.raises(ValueError, match="max_edge"):
        video_quality.score_video_quality("unused.mp4", max_edge=0)


def test_scores_to_metadata_keys() -> None:
    scores = video_quality.VideoQualityScores(
        blur_score=1.0,
        brightness_mean=2.0,
        underexposure_ratio=0.1,
        overexposure_ratio=0.2,
        lighting_score=0.3,
        motion_score=4.0,
    )
    meta = video_quality.scores_to_metadata(scores)
    assert set(meta) == {
        video_quality.BLUR_SCORE_KEY,
        video_quality.BRIGHTNESS_MEAN_KEY,
        video_quality.UNDEREXPOSURE_RATIO_KEY,
        video_quality.OVEREXPOSURE_RATIO_KEY,
        video_quality.LIGHTING_SCORE_KEY,
        video_quality.MOTION_SCORE_KEY,
    }
