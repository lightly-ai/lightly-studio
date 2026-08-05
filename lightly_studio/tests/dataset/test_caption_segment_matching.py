"""Unit tests for caption segment matching scores."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from pytest_mock import MockerFixture

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
    scores = caption_segment_matching._cosine_similarities(
        segment_embeddings=segment,
        caption_embeddings=caption,
    )
    assert scores[0] == pytest.approx(1.0)
    assert scores[1] == pytest.approx(1.0)
