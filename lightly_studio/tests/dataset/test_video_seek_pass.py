"""Unit tests for consolidated video seek-pass helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset import video_seek_pass
from lightly_studio.dataset.caption_segment_matching import (
    AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    CAPTION_SEGMENT_MATCH_SCORE_KEY,
    MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
)
from lightly_studio.dataset.video_quality import (
    BLUR_SCORE_KEY,
    VideoQualityScores,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_run_video_seek_pass__opens_once(mocker: MockerFixture) -> None:
    opened = MagicMock()
    opened.duration_s = 10.0
    open_cm = MagicMock()
    open_cm.__enter__.return_value = opened
    open_cm.__exit__.return_value = None
    open_mock = mocker.patch.object(video_seek_pass, "open_video_container", return_value=open_cm)

    quality = VideoQualityScores(
        blur_score=1.0,
        brightness_mean=128.0,
        underexposure_ratio=0.0,
        overexposure_ratio=0.0,
        lighting_score=1.0,
        motion_score=2.0,
        shake_score=0.5,
    )
    mocker.patch.object(video_seek_pass, "score_opened_video_quality", return_value=quality)

    generator = MagicMock()
    generator.embed_opened_video_segments.return_value = np.array(
        [[1.0, 0.0], [0.0, 1.0], [0.5, 0.5]],
        dtype=np.float32,
    )

    result = video_seek_pass.run_video_seek_pass(
        filepath="s3://bucket/video.mp4",
        compute_quality=True,
        embed_full_video=True,
        segment_intervals=[(0.0, 1.0), (1.0, 2.0)],
        embedding_generator=generator,
    )

    open_mock.assert_called_once_with("s3://bucket/video.mp4")
    generator.embed_opened_video_segments.assert_called_once_with(
        opened=opened,
        intervals=[(0.0, 10.0), (0.0, 1.0), (1.0, 2.0)],
    )
    assert result.quality_scores == quality
    assert result.full_video_embedding is not None
    assert np.allclose(result.full_video_embedding, [1.0, 0.0])
    assert result.segment_embeddings is not None
    assert result.segment_embeddings.shape == (2, 2)


def test_run_video_seek_pass__quality_only(mocker: MockerFixture) -> None:
    opened = MagicMock()
    open_cm = MagicMock()
    open_cm.__enter__.return_value = opened
    open_cm.__exit__.return_value = None
    mocker.patch.object(video_seek_pass, "open_video_container", return_value=open_cm)
    quality = VideoQualityScores(
        blur_score=1.0,
        brightness_mean=128.0,
        underexposure_ratio=0.0,
        overexposure_ratio=0.0,
        lighting_score=1.0,
        motion_score=2.0,
        shake_score=0.5,
    )
    mocker.patch.object(video_seek_pass, "score_opened_video_quality", return_value=quality)

    result = video_seek_pass.run_video_seek_pass(
        filepath="local.mp4",
        compute_quality=True,
    )

    assert result.quality_scores == quality
    assert result.segment_embeddings is None
    assert result.full_video_embedding is None


def test_score_quality_and_caption_segments__length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        video_seek_pass.score_quality_and_caption_segments(
            session=MagicMock(),
            video_sample_id=MagicMock(),
            video_path="unused.mp4",
            video_collection_id=MagicMock(),
            caption_sample_ids=[],
            intervals=[(0.0, 1.0)],
            caption_embeddings=[],
        )


def test_score_quality_and_caption_segments__persists(
    db_session: Session,
    mocker: MockerFixture,
) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]
    caption_id = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/caption_placeholder.mp4")],
    )[0]

    quality = VideoQualityScores(
        blur_score=12.0,
        brightness_mean=100.0,
        underexposure_ratio=0.1,
        overexposure_ratio=0.0,
        lighting_score=0.8,
        motion_score=3.0,
        shake_score=1.0,
    )
    mocker.patch.object(
        video_seek_pass,
        "run_video_seek_pass",
        return_value=video_seek_pass.VideoSeekPassResult(
            quality_scores=quality,
            segment_embeddings=np.array([[1.0, 0.0]], dtype=np.float32),
            full_video_embedding=None,
        ),
    )

    scores = video_seek_pass.score_quality_and_caption_segments(
        session=db_session,
        video_sample_id=video_sample_id,
        video_path="/path/to/video.mp4",
        video_collection_id=collection.collection_id,
        caption_sample_ids=[caption_id],
        intervals=[(0.0, 1.0)],
        caption_embeddings=[[1.0, 0.0]],
        compute_quality=True,
        embed_full_video=False,
    )

    assert scores[0] == pytest.approx(1.0)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=caption_id,
        key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(1.0)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(1.0)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(1.0)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=BLUR_SCORE_KEY,
    ) == pytest.approx(12.0)
