"""Unit tests for within-video caption repetition detection."""

from __future__ import annotations

import numpy as np
import pytest
from sqlmodel import Session

from lightly_studio.dataset import caption_repetition
from lightly_studio.dataset.caption_repetition import (
    REPEATED_CAPTION_GROUP_COUNT_KEY,
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY,
    find_repeated_captions,
    write_caption_repetition_metadata,
)
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import metadata_resolver
from tests.helpers_resolvers import create_caption, create_collection
from tests.resolvers.video.helpers import VideoStub, create_videos


def test_find_repeated_captions__empty() -> None:
    result = find_repeated_captions(caption_embeddings=[], intervals=[])
    assert result.matches == ()
    assert result.groups == ()


def test_find_repeated_captions__single() -> None:
    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0]],
        intervals=[(0.0, 1.0)],
    )
    assert result.matches == ()
    assert result.groups == ()


def test_find_repeated_captions__length_mismatch() -> None:
    with pytest.raises(ValueError, match="same length"):
        find_repeated_captions(
            caption_embeddings=[[1.0, 0.0]],
            intervals=[],
        )


def test_find_repeated_captions__invalid_threshold() -> None:
    with pytest.raises(ValueError, match="similarity_threshold"):
        find_repeated_captions(
            caption_embeddings=[[1.0, 0.0], [1.0, 0.0]],
            intervals=[(0.0, 1.0), (2.0, 3.0)],
            similarity_threshold=1.5,
        )


def test_find_repeated_captions__detects_separated_similar_pair() -> None:
    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]],
        intervals=[(0.0, 1.0), (1.0, 2.0), (3.0, 4.0)],
        similarity_threshold=0.9,
    )

    assert len(result.matches) == 1
    assert result.matches[0].index_a == 0
    assert result.matches[0].index_b == 2
    assert result.matches[0].similarity == pytest.approx(1.0)
    assert len(result.groups) == 1
    assert result.groups[0].member_indices == (0, 2)


def test_find_repeated_captions__ignores_overlapping_spans() -> None:
    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [1.0, 0.0]],
        intervals=[(0.0, 2.0), (1.0, 3.0)],
        similarity_threshold=0.9,
    )
    assert result.matches == ()
    assert result.groups == ()


def test_find_repeated_captions__respects_min_gap() -> None:
    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [1.0, 0.0]],
        intervals=[(0.0, 1.0), (1.5, 2.5)],
        similarity_threshold=0.9,
        min_gap_s=1.0,
    )
    assert result.matches == ()

    result_with_gap = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [1.0, 0.0]],
        intervals=[(0.0, 1.0), (2.5, 3.5)],
        similarity_threshold=0.9,
        min_gap_s=1.0,
    )
    assert len(result_with_gap.matches) == 1


def test_find_repeated_captions__clusters_full_clique() -> None:
    # A~B, B~C, and A~C (all identical) -> one group of three.
    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]],
        intervals=[(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)],
        similarity_threshold=0.9,
    )
    assert len(result.groups) == 1
    assert result.groups[0].member_indices == (0, 1, 2)
    assert len(result.matches) == 3


def test_find_repeated_captions__rejects_weak_bridge() -> None:
    # A~B and B~C are strong, but A~C is below threshold -> not one clique.
    # Unit vectors at 0°, 20°, 40°: AB/BC ≈ 0.94, AC ≈ 0.77.
    result = find_repeated_captions(
        caption_embeddings=[
            [1.0, 0.0],
            [0.9396926, 0.3420201],
            [0.7660444, 0.6427876],
        ],
        intervals=[(0.0, 1.0), (2.0, 3.0), (4.0, 5.0)],
        similarity_threshold=0.9,
    )
    assert len(result.groups) == 1
    assert len(result.groups[0].member_indices) == 2
    assert len(result.matches) == 2


def test_pairwise_cosine_similarities__unnormalized() -> None:
    matrix = caption_repetition._pairwise_cosine_similarities(
        embeddings=np.array([[2.0, 0.0], [3.0, 0.0]], dtype=np.float32)
    )
    assert matrix[0, 1] == pytest.approx(1.0)


def test_write_caption_repetition_metadata(db_session: Session) -> None:
    collection = create_collection(session=db_session, sample_type=SampleType.VIDEO)
    video_sample_ids = create_videos(
        session=db_session,
        collection_id=collection.collection_id,
        videos=[VideoStub(path="/path/to/video.mp4")],
    )
    video_sample_id = video_sample_ids[0]
    caption_a = create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=video_sample_id,
        text="typing",
    )
    caption_b = create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=video_sample_id,
        text="pouring",
    )
    caption_c = create_caption(
        session=db_session,
        collection_id=collection.collection_id,
        parent_sample_id=video_sample_id,
        text="typing again",
    )

    result = find_repeated_captions(
        caption_embeddings=[[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]],
        intervals=[(0.0, 1.0), (1.0, 2.0), (3.0, 4.0)],
        similarity_threshold=0.9,
    )
    write_caption_repetition_metadata(
        session=db_session,
        caption_sample_ids=[
            caption_a.sample_id,
            caption_b.sample_id,
            caption_c.sample_id,
        ],
        video_sample_id=video_sample_id,
        result=result,
        caption_embeddings=[[1.0, 0.0], [0.0, 1.0], [1.0, 0.0]],
    )

    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=caption_a.sample_id,
            key=REPEATED_CAPTION_GROUP_ID_KEY,
        )
        == 0
    )
    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=caption_c.sample_id,
            key=REPEATED_CAPTION_GROUP_ID_KEY,
        )
        == 0
    )
    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=caption_b.sample_id,
            key=REPEATED_CAPTION_GROUP_ID_KEY,
        )
        is None
    )
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=caption_a.sample_id,
        key=REPEATED_CAPTION_MAX_SIMILARITY_KEY,
    ) == pytest.approx(1.0)
    assert metadata_resolver.get_value_for_sample(
        session=db_session,
        sample_id=caption_b.sample_id,
        key=REPEATED_CAPTION_MAX_SIMILARITY_KEY,
    ) == pytest.approx(0.0)
    assert (
        metadata_resolver.get_value_for_sample(
            session=db_session,
            sample_id=video_sample_id,
            key=REPEATED_CAPTION_GROUP_COUNT_KEY,
        )
        == 1
    )
