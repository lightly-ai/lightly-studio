"""Unit tests for caption segment matching scores."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset import caption_segment_matching
from lightly_studio.dataset.caption_segment_matching import score_caption_segments


def test_score_caption_segments__empty() -> None:
    scores = score_caption_segments(
        video_path="unused.mp4",
        intervals=[],
        caption_embeddings=[],
    )
    assert scores == []


def test_score_caption_segments__length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        score_caption_segments(
            video_path="unused.mp4",
            intervals=[(0.0, 1.0)],
            caption_embeddings=[],
        )


def test_score_caption_segments__cosine_similarity(mocker: MockerFixture) -> None:
    generator = MagicMock()
    # Identical unit vectors -> score 1; orthogonal -> score 0.
    generator.embed_video_segments.return_value = np.array(
        [[1.0, 0.0], [0.0, 1.0]],
        dtype=np.float32,
    )
    mocker.patch.object(
        caption_segment_matching,
        "PerceptionEncoderEmbeddingGenerator",
        return_value=generator,
    )

    scores = score_caption_segments(
        video_path="unused.mp4",
        intervals=[(0.0, 1.0), (1.0, 2.0)],
        caption_embeddings=[[1.0, 0.0], [1.0, 0.0]],
    )

    assert len(scores) == 2
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(0.0)
    generator.embed_video_segments.assert_called_once_with(
        filepath="unused.mp4",
        intervals=[(0.0, 1.0), (1.0, 2.0)],
    )


def test_score_caption_segments__unnormalized_inputs(mocker: MockerFixture) -> None:
    generator = MagicMock()
    generator.embed_video_segments.return_value = np.array([[3.0, 0.0]], dtype=np.float32)
    mocker.patch.object(
        caption_segment_matching,
        "PerceptionEncoderEmbeddingGenerator",
        return_value=generator,
    )

    scores = score_caption_segments(
        video_path="unused.mp4",
        intervals=[(0.0, 1.0)],
        caption_embeddings=[[2.0, 0.0]],
    )

    assert scores[0] == pytest.approx(1.0)


def test_cosine_similarities() -> None:
    segment = np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    caption = np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    scores = caption_segment_matching.cosine_similarities(
        segment_embeddings=segment,
        caption_embeddings=caption,
    )
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(1.0)


def test_set_video_caption_match_aggregates(db_session: Session) -> None:
    from lightly_studio.dataset.caption_segment_matching import (
        AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        set_video_caption_match_aggregates,
    )
    from lightly_studio.models.collection import SampleType
    from lightly_studio.resolvers import metadata_resolver
    from tests.helpers_resolvers import create_collection
    from tests.resolvers.video.helpers import VideoStub, create_videos

    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]

    set_video_caption_match_aggregates(
        session=db_session,
        video_sample_id=video_sample_id,
        scores=[0.2, 0.8, 0.5],
    )

    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(0.2)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(0.5)


def test_set_video_caption_match_aggregates__empty_noop(db_session: Session) -> None:
    from lightly_studio.dataset.caption_segment_matching import (
        MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        set_video_caption_match_aggregates,
    )
    from lightly_studio.models.collection import SampleType
    from lightly_studio.resolvers import metadata_resolver
    from tests.helpers_resolvers import create_collection
    from tests.resolvers.video.helpers import VideoStub, create_videos

    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]

    set_video_caption_match_aggregates(
        session=db_session,
        video_sample_id=video_sample_id,
        scores=[],
    )

    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=video_sample_id,
            key=MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        )
        is None
    )
