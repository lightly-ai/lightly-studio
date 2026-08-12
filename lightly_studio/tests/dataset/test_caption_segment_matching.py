"""Unit tests for caption segment matching scores."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture
from sqlmodel import Session

from lightly_studio.dataset import caption_segment_matching
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_score_caption_segments__empty() -> None:
    scores = caption_segment_matching.score_caption_segments(
        video_path="unused.mp4",
        intervals=[],
        caption_embeddings=[],
    )
    assert scores == []


def test_score_caption_segments__length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        caption_segment_matching.score_caption_segments(
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

    scores = caption_segment_matching.score_caption_segments(
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

    scores = caption_segment_matching.score_caption_segments(
        video_path="unused.mp4",
        intervals=[(0.0, 1.0)],
        caption_embeddings=[[2.0, 0.0]],
    )

    assert scores[0] == pytest.approx(1.0)


def test_score_caption_segment_frames() -> None:
    generator = MagicMock()
    generator.embed_video_segment_frames.return_value = np.array(
        [
            [[1.0, 0.0], [0.8, 0.6], [0.0, 1.0]],
            [[0.0, 1.0], [0.6, 0.8], [1.0, 0.0]],
            [[-1.0, 0.0], [-0.8, 0.6], [0.0, 1.0]],
        ],
        dtype=np.float32,
    )

    scores = caption_segment_matching.score_caption_segment_frames(
        video_path="unused.mp4",
        intervals=[(0.0, 1.0), (1.0, 2.0), (2.0, 3.0)],
        caption_embeddings=[[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]],
        embedding_generator=generator,
        top_k=2,
    )

    assert scores.mean_pooled_scores == pytest.approx((0.7474, 0.7474, 0.7474), abs=1e-4)
    assert scores.top_k_scores == pytest.approx((0.9, 0.9, 0.9))
    assert scores.hard_negative_scores == pytest.approx((0.8, 0.8, -0.3))
    assert scores.alignment_margins == pytest.approx((0.1, 0.1, 1.2))


def test_score_caption_segment_frames__overlapping_segments_are_not_negatives() -> None:
    generator = MagicMock()
    generator.embed_video_segment_frames.return_value = np.array(
        [
            [[1.0, 0.0], [1.0, 0.0]],
            [[0.0, 1.0], [0.0, 1.0]],
        ],
        dtype=np.float32,
    )

    scores = caption_segment_matching.score_caption_segment_frames(
        video_path="unused.mp4",
        intervals=[(0.0, 2.0), (1.0, 3.0)],
        caption_embeddings=[[1.0, 0.0], [0.0, 1.0]],
        embedding_generator=generator,
    )

    assert scores.hard_negative_scores == (None, None)
    assert scores.alignment_margins == (None, None)


def test_score_caption_segment_frames__invalid_top_k() -> None:
    generator = MagicMock()
    generator.embed_video_segment_frames.return_value = np.ones((1, 2, 2), dtype=np.float32)

    with pytest.raises(ValueError, match="top_k"):
        caption_segment_matching.score_caption_segment_frames(
            video_path="unused.mp4",
            intervals=[(0.0, 1.0)],
            caption_embeddings=[[1.0, 0.0]],
            embedding_generator=generator,
            top_k=3,
        )


def test_cosine_similarities() -> None:
    segment = np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    caption = np.array([[1.0, 0.0], [1.0, 1.0]], dtype=np.float32)
    scores = caption_segment_matching._cosine_similarities(
        segment_embeddings=segment,
        caption_embeddings=caption,
    )
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(1.0)


def test_set_video_caption_match_aggregates(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]

    caption_segment_matching.set_video_caption_match_aggregates(
        session=db_session,
        video_sample_id=video_sample_id,
        scores=[0.2, 0.8, 0.5],
    )

    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=caption_segment_matching.MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(0.2)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=caption_segment_matching.AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
    ) == pytest.approx(0.5)


def test_set_video_caption_match_aggregates__empty_noop(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]

    caption_segment_matching.set_video_caption_match_aggregates(
        session=db_session,
        video_sample_id=video_sample_id,
        scores=[],
    )

    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=video_sample_id,
            key=caption_segment_matching.MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        )
        is None
    )


def test_set_video_caption_frame_score_aggregates(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_id = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )[0]
    scores = caption_segment_matching.CaptionSegmentFrameScores(
        mean_pooled_scores=(0.2, 0.6),
        top_k_scores=(0.3, 0.7),
        hard_negative_scores=(0.1, None),
        alignment_margins=(0.2, None),
    )

    caption_segment_matching.set_video_caption_frame_score_aggregates(
        session=db_session,
        video_sample_id=video_sample_id,
        scores=scores,
    )

    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=caption_segment_matching.MIN_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY,
    ) == pytest.approx(0.3)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=caption_segment_matching.AVG_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY,
    ) == pytest.approx(0.5)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=video_sample_id,
        key=caption_segment_matching.MIN_CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY,
    ) == pytest.approx(0.2)
