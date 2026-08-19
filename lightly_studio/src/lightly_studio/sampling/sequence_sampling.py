"""Database-backed video sequence sampling."""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Iterable, Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import collection_resolver, video_frame_resolver
from lightly_studio.sampling import sampling_helpers, sequence_selection
from lightly_studio.sampling.mundig import Mundig
from lightly_studio.sampling.sampling_config import EmbeddingDiversityStrategy, SamplingConfig

logger = logging.getLogger(__name__)


def sampling_via_database_sequences(
    session: Session,
    config: SamplingConfig,
    input_sample_ids: list[UUID],
    preselected_sample_ids: Iterable[UUID] | None = None,
) -> None:
    """Run mean-proxy sequence sampling on a VIDEO_FRAME collection.

    Args:
        session: Database session used to resolve and store sampling data.
        config: Sampling configuration. ``selected_sequence_length`` must be set.
        input_sample_ids: Candidate frame sample IDs.
        preselected_sample_ids: Frame sample IDs that should inform the sampling as
            already selected. Sequences holding such a frame are excluded from the
            result tag; frames outside the candidate sequences are ignored.
    """
    diversity_strategies = _validate_sequence_sampling(session=session, config=config)
    sequence_length = config.selected_sequence_length
    assert sequence_length is not None
    sequences = _load_sequences(
        session=session,
        sample_ids=input_sample_ids,
        sequence_length=sequence_length,
    )
    preselected_indices = _get_preselected_sequence_indices(
        sequences=sequences,
        preselected_sample_ids=preselected_sample_ids,
    )
    n_sequences_to_select = min(
        config.n_samples_to_select // sequence_length,
        len(sequences) - len(preselected_indices),
    )
    if n_sequences_to_select == 0:
        logger.warning(
            "No sequences available for sampling. No video has at least "
            f"{sequence_length} candidate frame(s) outside the preselection."
        )
        return

    # Flattened in sequence order: `get_embeddings_by_sample_ids` returns embeddings in
    # this same order, which is what lets the reshape below group them positionally.
    frame_sample_ids = [sample_id for sequence in sequences for sample_id in sequence]
    mundig = Mundig()
    for strat in diversity_strategies:
        frame_embeddings = sampling_helpers.get_embeddings_by_sample_ids(
            session=session,
            collection_id=config.collection_id,
            sample_ids=frame_sample_ids,
            embedding_model_name=strat.embedding_model_name,
        )
        if len(frame_embeddings) != len(frame_sample_ids):
            raise ValueError(
                "Expected an embedding for every input sample, got "
                f"{len(frame_embeddings)} embeddings for {len(frame_sample_ids)} samples."
            )
        # Mean-pool each sequence's frame embeddings into a single proxy vector.
        sequence_proxies: NDArray[np.float32] = (
            np.asarray(frame_embeddings, dtype=np.float32)
            .reshape(len(sequences), sequence_length, -1)
            .mean(axis=1)
        )
        mundig.add_diversity(embeddings=sequence_proxies, strength=strat.strength)
    # Mundig returns the preselected sequences as the prefix of the selection.
    selected_sequence_indices = mundig.run(
        n_samples=len(preselected_indices) + n_sequences_to_select,
        preselected_indices=preselected_indices,
    )
    sampling_helpers.create_result_tag(
        session=session,
        collection_id=config.collection_id,
        tag_name=config.sampling_result_tag_name,
        selected_sample_ids=[
            sample_id
            for index in selected_sequence_indices[len(preselected_indices) :]
            for sample_id in sequences[index]
        ],
    )


def _validate_sequence_sampling(
    session: Session,
    config: SamplingConfig,
) -> list[EmbeddingDiversityStrategy]:
    """Check that the config can run as sequence sampling and return its strategies.

    Args:
        session: The database session.
        config: The sampling configuration. ``selected_sequence_length`` must be set.

    Returns:
        The configured diversity strategies.

    Raises:
        ValueError: If the collection is not a VIDEO_FRAME collection, if
            ``n_samples_to_select`` is not a multiple of ``selected_sequence_length``,
            or if any non-diversity strategy is configured.
    """
    sequence_length = config.selected_sequence_length
    assert sequence_length is not None
    collection_resolver.check_collection_type(
        session=session,
        collection_id=config.collection_id,
        expected_type=SampleType.VIDEO_FRAME,
    )
    if config.n_samples_to_select % sequence_length != 0:
        raise ValueError(
            f"n_samples_to_select ({config.n_samples_to_select}) must be a multiple "
            f"of selected_sequence_length ({sequence_length})."
        )
    diversity_strategies: list[EmbeddingDiversityStrategy] = []
    non_diversity_names: list[str] = []
    for strat in config.strategies:
        if isinstance(strat, EmbeddingDiversityStrategy):
            diversity_strategies.append(strat)
        else:
            non_diversity_names.append(type(strat).__name__)
    if non_diversity_names:
        raise ValueError(
            "selected_sequence_length currently supports only diversity strategies, "
            f"got: {non_diversity_names}."
        )
    return diversity_strategies


def _load_sequences(
    session: Session,
    sample_ids: Sequence[UUID],
    sequence_length: int,
) -> list[list[UUID]]:
    """Load candidate frames and chunk them into complete sequences."""
    frames = video_frame_resolver.get_frame_infos_by_ids(session=session, sample_ids=sample_ids)
    if len(frames) != len(sample_ids):
        missing = len(sample_ids) - len(frames)
        raise ValueError(
            "Sequence sampling requires all candidates to be video frames; "
            f"{missing} sample(s) have no video frame metadata."
        )
    sequences = sequence_selection.create_sequences(frames=frames, sequence_length=sequence_length)
    n_dropped = len(frames) - len(sequences) * sequence_length
    if n_dropped > 0:
        logger.warning(
            f"Dropped {n_dropped} of {len(frames)} candidate frame(s) that do not fill a "
            f"complete sequence of {sequence_length} frame(s)."
        )
    return sequences


def _get_preselected_sequence_indices(
    sequences: Sequence[Sequence[UUID]],
    preselected_sample_ids: Iterable[UUID] | None,
) -> list[int]:
    """Map preselected frames onto the sequences they cover.

    Selection happens over sequences, so preselection has to be expressed per
    sequence too. Sequence boundaries follow from the candidate frames, so a
    preselection made over different candidates can reach frames outside the
    sequences of this run or cover a sequence only partially. Frames outside the
    sequences carry no information for this run and are ignored, while a sequence
    with at least one preselected frame counts as preselected, because selecting it
    again would overlap what is already selected.

    Args:
        sequences: Sequences of frame sample ids built from the candidate frames.
        preselected_sample_ids: Frame sample ids to treat as already selected.

    Returns:
        Ascending indices into ``sequences`` of the preselected sequences.
    """
    preselected = set(preselected_sample_ids or ())
    sequence_index_by_frame = {
        sample_id: index for index, sequence in enumerate(sequences) for sample_id in sequence
    }
    n_covered_frames: Counter[int] = Counter(
        sequence_index_by_frame[sample_id]
        for sample_id in preselected
        if sample_id in sequence_index_by_frame
    )

    n_ignored = len(preselected) - sum(n_covered_frames.values())
    if n_ignored > 0:
        logger.info(
            f"Ignored {n_ignored} of {len(preselected)} preselected frame(s) that are not part "
            "of a complete candidate sequence."
        )
    n_partially_covered = sum(
        n_frames != len(sequences[index]) for index, n_frames in n_covered_frames.items()
    )
    if n_partially_covered > 0:
        logger.info(
            f"Preselection covers {n_partially_covered} sequence(s) only partially; they count "
            "as preselected and stay out of the result."
        )
    return sorted(n_covered_frames)
