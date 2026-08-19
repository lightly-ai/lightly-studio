"""Test database-backed video sequence sampling."""

from __future__ import annotations

import logging
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import tag_resolver, video_frame_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_frame_resolver.video_frame_filter import VideoFrameFilter
from lightly_studio.sampling.sampling_config import (
    EmbeddingDiversityStrategy,
    MetadataWeightingStrategy,
    SamplingConfig,
)
from lightly_studio.sampling.sampling_via_db import sampling_via_database
from lightly_studio.sampling.sequence_sampling import sampling_via_database_sequences
from tests import helpers_resolvers
from tests.resolvers.video.helpers import VideoStub, create_video_with_frames


def test_sampling_via_database_sequences(
    db_session: Session,
) -> None:
    """Mean-proxy diversity tags the first and last of three sequences.

    Embeddings are ``[i, i]`` per frame, so the three sequence proxies sit at
    ``[2, 2]``, ``[7, 7]``, and ``[12, 12]``. Selecting two sequences must tag
    the ends; a wrong reshape would mix frames across sequences and pick a
    different pair.
    """
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=15,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=10,  # 2 of 3 sequences of length 5
        sampling_result_tag_name="sequence_sampling",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    sampling_via_database_sequences(
        session=db_session,
        config=sampling_config,
        input_sample_ids=frame_sample_ids,
    )

    tags = tag_resolver.get_all_by_collection_id(
        session=db_session, collection_id=frame_collection_id
    )
    assert len(tags) == 1
    assert tags[0].name == "sequence_sampling"

    tagged = video_frame_resolver.get_all_by_collection_id(
        session=db_session,
        collection_id=frame_collection_id,
        video_frame_filter=VideoFrameFilter(sample_filter=SampleFilter(tag_ids=[tags[0].tag_id])),
    )
    tagged_ids = {frame.sample_id for frame in tagged.samples}
    first_sequence = set(frame_sample_ids[0:5])
    last_sequence = set(frame_sample_ids[10:15])
    assert tagged_ids == first_sequence | last_sequence
    assert sorted(frame.frame_number for frame in tagged.samples) == [
        0,
        1,
        2,
        3,
        4,
        10,
        11,
        12,
        13,
        14,
    ]


def test_sampling_via_database_sequences__rejects_non_multiple(
    db_session: Session,
) -> None:
    """n_samples_to_select must be a multiple of selected_sequence_length."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=10,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=7,
        sampling_result_tag_name="bad_n",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with pytest.raises(ValueError, match="must be a multiple"):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
        )


def test_sampling_via_database_sequences__rejects_non_frame_collection(
    db_session: Session,
) -> None:
    """selected_sequence_length > 1 requires a VIDEO_FRAME collection."""
    collection = helpers_resolvers.create_collection(
        session=db_session, sample_type=SampleType.IMAGE
    )
    sample_ids = [
        helpers_resolvers.create_image(
            session=db_session,
            collection_id=collection.collection_id,
            file_path_abs=f"/data/sample_{i}.jpg",
        ).sample_id
        for i in range(4)
    ]

    sampling_config = SamplingConfig(
        collection_id=collection.collection_id,
        n_samples_to_select=4,
        sampling_result_tag_name="bad_collection",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=2,
    )

    with pytest.raises(ValueError, match="expected 'video_frame'"):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=sample_ids,
        )


def test_sampling_via_database_sequences__rejects_non_diversity(
    db_session: Session,
) -> None:
    """Sequence sampling currently supports diversity strategies only."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=10,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="bad_strategy",
        strategies=[MetadataWeightingStrategy(metadata_key="score")],
        selected_sequence_length=5,
    )

    with pytest.raises(ValueError, match="only diversity"):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
        )


def test_sampling_via_database_sequences__warns_when_too_few_frames(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Too few frames logs a warning and returns without creating a tag."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=3,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="too_few",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with caplog.at_level(logging.WARNING):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
        )

    assert "No sequences available for sampling." in caplog.text
    tags = tag_resolver.get_all_by_collection_id(
        session=db_session, collection_id=frame_collection_id
    )
    assert tags == []


def test_sampling_via_database_sequences__warns_about_dropped_frames(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Frames of an incomplete trailing sequence are reported, not dropped silently."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=12,  # 2 sequences of length 5, 2 frames left over
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=10,
        sampling_result_tag_name="dropped_tail",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with caplog.at_level(logging.WARNING):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
        )

    assert "Dropped 2 of 12 candidate frame(s)" in caplog.text
    assert _tagged_frame_numbers(
        session=db_session,
        collection_id=frame_collection_id,
        tag_name="dropped_tail",
    ) == list(range(10))


def test_sampling_via_database_sequences__preselection(
    db_session: Session,
) -> None:
    """A preselected sequence informs the selection and stays out of the tag.

    Sequence proxies sit at ``[2, 2]``, ``[7, 7]`` and ``[12, 12]``. With the
    first sequence preselected, diversity must pick the far end rather than the
    adjacent middle sequence.
    """
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=15,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,  # 1 sequence of length 5, on top of the preselected one
        sampling_result_tag_name="preselected_sequence",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    sampling_via_database_sequences(
        session=db_session,
        config=sampling_config,
        input_sample_ids=frame_sample_ids,
        preselected_sample_ids=frame_sample_ids[0:5],
    )

    assert _tagged_frame_numbers(
        session=db_session,
        collection_id=frame_collection_id,
        tag_name="preselected_sequence",
    ) == [10, 11, 12, 13, 14]


def test_sampling_via_database_sequences__preselection_partial_sequence(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A partially preselected sequence counts as preselected and stays out of the tag.

    Sequence boundaries come from the candidate frames, so a preselection made over
    other candidates can straddle them. Selecting such a sequence again would overlap
    the preselection, so it is skipped instead of rejected.
    """
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=10,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="partial_preselection",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with caplog.at_level(logging.INFO):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
            preselected_sample_ids=frame_sample_ids[0:3],
        )

    assert "covers 1 sequence(s) only partially" in caplog.text
    assert _tagged_frame_numbers(
        session=db_session,
        collection_id=frame_collection_id,
        tag_name="partial_preselection",
    ) == [5, 6, 7, 8, 9]


def test_sampling_via_database_sequences__preselection_ignores_dropped_frame(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A preselected frame in the dropped trailing chunk is ignored, not rejected."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=12,  # 2 sequences of length 5, frames 10 and 11 do not fill one
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="dropped_preselection",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with caplog.at_level(logging.INFO):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids,
            preselected_sample_ids=[frame_sample_ids[10]],
        )

    assert "Ignored 1 of 1 preselected frame(s)" in caplog.text
    tagged_frame_numbers = _tagged_frame_numbers(
        session=db_session,
        collection_id=frame_collection_id,
        tag_name="dropped_preselection",
    )
    # Nothing counts as preselected, so both sequences stay available and either can win.
    assert tagged_frame_numbers in ([0, 1, 2, 3, 4], [5, 6, 7, 8, 9])


def test_sampling_via_database_sequences__preselection_ignores_frame_outside_input(
    db_session: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Preselected frames that are no candidates at all are ignored."""
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=10,
    )

    sampling_config = SamplingConfig(
        collection_id=frame_collection_id,
        n_samples_to_select=5,
        sampling_result_tag_name="outside_preselection",
        strategies=[EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")],
        selected_sequence_length=5,
    )

    with caplog.at_level(logging.INFO):
        sampling_via_database_sequences(
            session=db_session,
            config=sampling_config,
            input_sample_ids=frame_sample_ids[0:5],
            preselected_sample_ids=frame_sample_ids[5:10],
        )

    assert "Ignored 5 of 5 preselected frame(s)" in caplog.text
    assert _tagged_frame_numbers(
        session=db_session,
        collection_id=frame_collection_id,
        tag_name="outside_preselection",
    ) == [0, 1, 2, 3, 4]


def test_sampling_via_database__sequence_preselection_matches_single_sampling(
    db_session: Session,
) -> None:
    """Selecting two sequences in two preselected steps matches one combined run.

    Goes through ``sampling_via_database`` so that resolving ``preselected_tag_name``
    into frames of the sequence path is covered too.
    """
    frame_collection_id, frame_sample_ids = _fill_db_with_video_frames_and_embeddings(
        session=db_session,
        n_frames=15,
    )
    strategy = EmbeddingDiversityStrategy(embedding_model_name="embedding_model_1")

    def sample_sequences(
        n_samples_to_select: int, tag_name: str, preselected_tag_name: str | None
    ) -> list[int]:
        sampling_via_database(
            session=db_session,
            config=SamplingConfig(
                collection_id=frame_collection_id,
                n_samples_to_select=n_samples_to_select,
                sampling_result_tag_name=tag_name,
                preselected_tag_name=preselected_tag_name,
                strategies=[strategy],
                selected_sequence_length=5,
            ),
            input_sample_ids=frame_sample_ids,
        )
        return _tagged_frame_numbers(
            session=db_session, collection_id=frame_collection_id, tag_name=tag_name
        )

    first_batch = sample_sequences(
        n_samples_to_select=5, tag_name="first_batch", preselected_tag_name=None
    )
    second_batch = sample_sequences(
        n_samples_to_select=5, tag_name="second_batch", preselected_tag_name="first_batch"
    )
    single_batch = sample_sequences(
        n_samples_to_select=10, tag_name="single_batch", preselected_tag_name=None
    )

    assert len(first_batch) == 5
    assert set(first_batch).isdisjoint(second_batch)
    assert set(first_batch + second_batch) == set(single_batch)


def _tagged_frame_numbers(session: Session, collection_id: UUID, tag_name: str) -> list[int]:
    """Return the ascending frame numbers carrying the tag with the given name."""
    tag = tag_resolver.get_by_name(session=session, tag_name=tag_name, collection_id=collection_id)
    assert tag is not None
    frames = video_frame_resolver.get_all_by_collection_id(
        session=session,
        collection_id=collection_id,
        video_frame_filter=VideoFrameFilter(sample_filter=SampleFilter(tag_ids=[tag.tag_id])),
    )
    return sorted(frame.frame_number for frame in frames.samples)


def _fill_db_with_video_frames_and_embeddings(
    session: Session,
    *,
    n_frames: int,
    embedding_model_name: str = "embedding_model_1",
) -> tuple[UUID, list[UUID]]:
    """Create a video with ``n_frames`` frames and per-frame embeddings.

    Embeddings are ``[i, i]`` for frame index ``i`` so diversity prefers
    sequences at opposite ends of the video.

    Returns:
        Frame collection id and ordered frame sample ids.
    """
    video_collection = helpers_resolvers.create_collection(
        session=session, sample_type=SampleType.VIDEO
    )
    video_with_frames = create_video_with_frames(
        session=session,
        collection_id=video_collection.collection_id,
        video=VideoStub(
            path="/data/sequence_test.mp4",
            duration_s=float(n_frames),
            fps=1.0,
        ),
    )
    frame_collection_id = video_with_frames.video_frames_collection_id
    frame_sample_ids = list(video_with_frames.frame_sample_ids)
    embedding_model = helpers_resolvers.create_embedding_model(
        session=session,
        collection_id=frame_collection_id,
        embedding_model_name=embedding_model_name,
        embedding_dimension=2,
    )
    for i, frame_sample_id in enumerate(frame_sample_ids):
        helpers_resolvers.create_sample_embedding(
            session=session,
            sample_id=frame_sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[float(i), float(i)],
        )
    return frame_collection_id, frame_sample_ids
