"""Tests for deterministic egocentric dataset requirements."""

from __future__ import annotations

from pathlib import Path

import pytest

from lightly_studio.dataset import egocentric_qa
from lightly_studio.dataset.whisper_transcript import TimedTranscriptCaption
from tests.resolvers.video import helpers as video_helpers


@pytest.mark.parametrize(("width", "height"), [(1920, 1080), (1080, 1920), (3840, 2160)])
def test_has_minimum_1080p_resolution__accepted(width: int, height: int) -> None:
    assert egocentric_qa.has_minimum_1080p_resolution(width=width, height=height)


@pytest.mark.parametrize(("width", "height"), [(1919, 1080), (1920, 1079), (1280, 720)])
def test_has_minimum_1080p_resolution__rejected(width: int, height: int) -> None:
    assert not egocentric_qa.has_minimum_1080p_resolution(width=width, height=height)


@pytest.mark.parametrize("duration_s", [60.0, 300.0, 1200.0])
def test_has_valid_duration__accepted(duration_s: float) -> None:
    assert egocentric_qa.has_valid_duration(duration_s=duration_s)


@pytest.mark.parametrize("duration_s", [None, 0.0, 59.9, 1200.1, float("nan")])
def test_has_valid_duration__rejected(duration_s: float | None) -> None:
    assert not egocentric_qa.has_valid_duration(duration_s=duration_s)


def test_orientation_and_preferred_format() -> None:
    assert egocentric_qa.get_orientation(width=1920, height=1080) == "landscape"
    assert egocentric_qa.get_orientation(width=1080, height=1920) == "portrait"
    assert egocentric_qa.get_orientation(width=1080, height=1080) == "square"
    assert egocentric_qa.has_preferred_video_format("example.MP4")
    assert not egocentric_qa.has_preferred_video_format("example.mov")


def test_has_audio_stream__silent_video(tmp_path: Path) -> None:
    video_path = video_helpers.create_video_file(
        output_path=tmp_path / "silent.mp4",
        num_frames=2,
        fps=1,
    )

    assert not egocentric_qa.has_audio_stream(video_path=str(video_path))


def test_has_valid_caption_timestamps__accepts_ordered_overlap() -> None:
    captions = (
        TimedTranscriptCaption(text="First", start_time_s=0.0, end_time_s=3.0),
        TimedTranscriptCaption(text="Second", start_time_s=2.0, end_time_s=4.0),
    )

    assert egocentric_qa.has_valid_caption_timestamps(captions=captions, duration_s=4.0)


@pytest.mark.parametrize(
    ("captions", "duration_s"),
    [
        ((), 10.0),
        ((TimedTranscriptCaption(text="Bad", start_time_s=-1.0, end_time_s=1.0),), 10.0),
        ((TimedTranscriptCaption(text="Bad", start_time_s=1.0, end_time_s=1.0),), 10.0),
        ((TimedTranscriptCaption(text="Bad", start_time_s=9.0, end_time_s=11.0),), 10.0),
        (
            (
                TimedTranscriptCaption(text="Later", start_time_s=5.0, end_time_s=6.0),
                TimedTranscriptCaption(text="Earlier", start_time_s=2.0, end_time_s=3.0),
            ),
            10.0,
        ),
    ],
)
def test_has_valid_caption_timestamps__rejects_invalid_values(
    captions: tuple[TimedTranscriptCaption, ...],
    duration_s: float,
) -> None:
    assert not egocentric_qa.has_valid_caption_timestamps(
        captions=captions,
        duration_s=duration_s,
    )


def test_summarize_dataset__passes_supported_distribution() -> None:
    summary = egocentric_qa.summarize_dataset(
        records=[
            egocentric_qa.DatasetVideoQa(
                duration_s=120.0,
                language="en",
                is_static_camera=False,
            ),
            egocentric_qa.DatasetVideoQa(
                duration_s=240.0,
                language="de",
                is_static_camera=True,
            ),
            egocentric_qa.DatasetVideoQa(
                duration_s=180.0,
                language="en-US",
                is_static_camera=False,
            ),
        ]
    )

    assert summary.average_duration_s == pytest.approx(180.0)
    assert summary.average_duration_pass
    assert summary.english_video_count == 2
    assert summary.english_video_ratio == pytest.approx(2 / 3)
    assert summary.english_video_ratio_pass
    assert summary.static_camera_count == 1
    assert summary.static_camera_ratio == pytest.approx(1 / 3)
    assert summary.static_camera_minority_pass


def test_summarize_dataset__fails_missing_duration_and_half_static() -> None:
    summary = egocentric_qa.summarize_dataset(
        records=[
            egocentric_qa.DatasetVideoQa(
                duration_s=None,
                language=None,
                is_static_camera=True,
            ),
            egocentric_qa.DatasetVideoQa(
                duration_s=600.0,
                language="de",
                is_static_camera=False,
            ),
        ]
    )

    assert not summary.average_duration_pass
    assert not summary.english_video_ratio_pass
    assert not summary.static_camera_minority_pass
