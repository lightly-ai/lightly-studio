"""Unit tests for timed caption helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlmodel import Session

from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.dataset import timed_captions
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import caption_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_video


def test_buffered_interval__no_buffer() -> None:
    assert timed_captions._buffered_interval(
        start_time_s=1.0,
        end_time_s=3.0,
        buffer_ratio=0.0,
    ) == (1.0, 3.0)


def test_buffered_interval__expands_and_clamps_start() -> None:
    assert timed_captions._buffered_interval(
        start_time_s=0.2,
        end_time_s=1.2,
        buffer_ratio=0.1,
    ) == pytest.approx((0.1, 1.3))
    assert timed_captions._buffered_interval(
        start_time_s=0.05,
        end_time_s=1.05,
        buffer_ratio=0.1,
    ) == pytest.approx((0.0, 1.15))


def test_add_captions_from_sentences(db_session: Session, tmp_path: Path) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_table = create_video(
        session=db_session,
        collection_id=collection.collection_id,
        video=VideoStub(path="/path/to/video.mp4"),
    )
    video = VideoSample(inner=video_table)
    sentences_path = tmp_path / "sentences.json"
    sentences_path.write_text(
        json.dumps(
            {
                "sentences": [
                    {"text": "second", "start": 2.0, "end": 3.0},
                    {"text": "first", "start": 0.5, "end": 1.5},
                ]
            }
        ),
        encoding="utf-8",
    )

    caption_ids = timed_captions.add_captions_from_sentences(
        video=video,
        sentences_path=sentences_path,
    )
    captions = caption_resolver.get_by_ids(session=db_session, sample_ids=caption_ids)

    assert [caption.text for caption in captions] == ["first", "second"]
    assert captions[0].temporal_span_details is not None
    assert captions[0].temporal_span_details.start_time_s == pytest.approx(0.5)
