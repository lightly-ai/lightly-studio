"""Detect repeated actions within a video via caption-text embedding similarity.

Prototype helper: given timed caption embeddings for a single parent video, finds
pairs whose text embeddings are similar and whose temporal spans are separated,
then clusters them into repetition groups. Callers typically store
``repeated_caption_group_id`` / ``repeated_caption_max_similarity`` on each
caption sample, and ``repeated_caption_group_count`` on the parent video.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.resolvers import metadata_resolver

REPEATED_CAPTION_GROUP_ID_KEY = "repeated_caption_group_id"
REPEATED_CAPTION_MAX_SIMILARITY_KEY = "repeated_caption_max_similarity"
REPEATED_CAPTION_GROUP_COUNT_KEY = "repeated_caption_group_count"

# Default PE text cosine threshold; tune per caption style / model.
# 0.85 filters weak false positives (e.g. unrelated long captions vs short labels).
DEFAULT_SIMILARITY_THRESHOLD = 0.85
_MIN_CAPTIONS_FOR_PAIRWISE = 2


@dataclass(frozen=True)
class CaptionRepetitionMatch:
    """A temporally separated caption pair above the similarity threshold."""

    index_a: int
    index_b: int
    similarity: float


@dataclass(frozen=True)
class CaptionRepetitionGroup:
    """Clique of captions where every pair is a repetition match."""

    group_id: int
    member_indices: tuple[int, ...]


@dataclass(frozen=True)
class CaptionRepetitionResult:
    """Repetition matches and groups for one video's timed captions."""

    matches: tuple[CaptionRepetitionMatch, ...]
    groups: tuple[CaptionRepetitionGroup, ...]


def find_repeated_captions(
    caption_embeddings: Sequence[Sequence[float]],
    intervals: Sequence[tuple[float, float]],
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    min_gap_s: float = 0.0,
) -> CaptionRepetitionResult:
    """Find repeated timed captions via pairwise text-embedding similarity.

    Compares caption embeddings within one video. A pair counts as a repetition
    when cosine similarity is ``>= similarity_threshold`` and the spans do not
    overlap (optionally requiring ``min_gap_s`` between them). Groups are
    cliques: every pair in a group must be a qualifying match, so a weak bridge
    cannot pull an unrelated caption into a tight cluster.

    Args:
        caption_embeddings: Caption text embedding vectors, one per interval.
        intervals: ``(start_time_s, end_time_s)`` pairs aligned with embeddings.
        similarity_threshold: Minimum cosine similarity to link two captions.
        min_gap_s: Minimum seconds between the earlier span's end and the later
            span's start. ``0`` only requires non-overlapping spans.

    Returns:
        Matches and clique groups (group ids are ``0 .. G-1``).

    Raises:
        ValueError: If list lengths differ, an interval is invalid, or
            ``similarity_threshold`` / ``min_gap_s`` are out of range.
    """
    if len(caption_embeddings) != len(intervals):
        raise ValueError(
            f"caption_embeddings and intervals must have the same length, "
            f"got {len(caption_embeddings)} and {len(intervals)}."
        )
    if not (0.0 <= similarity_threshold <= 1.0):
        raise ValueError(f"similarity_threshold must be in [0, 1], got {similarity_threshold}.")
    if min_gap_s < 0.0:
        raise ValueError(f"min_gap_s must be >= 0, got {min_gap_s}.")
    _validate_intervals(intervals)

    if len(intervals) < _MIN_CAPTIONS_FOR_PAIRWISE:
        return CaptionRepetitionResult(matches=(), groups=())

    similarity_matrix = _pairwise_cosine_similarities(
        embeddings=np.asarray(caption_embeddings, dtype=np.float32)
    )
    matches = _collect_matches(
        similarity_matrix=similarity_matrix,
        intervals=intervals,
        similarity_threshold=similarity_threshold,
        min_gap_s=min_gap_s,
    )
    groups = _clique_groups(matches=matches)
    return CaptionRepetitionResult(matches=tuple(matches), groups=tuple(groups))


def write_caption_repetition_metadata(
    session: Session,
    *,
    caption_sample_ids: Sequence[UUID],
    video_sample_id: UUID,
    result: CaptionRepetitionResult,
    caption_embeddings: Sequence[Sequence[float]] | None = None,
) -> None:
    """Write repetition group ids and max pairwise similarity as metadata.

    Captions that belong to a group get ``repeated_caption_group_id``. When
    ``caption_embeddings`` is provided, every caption also gets
    ``repeated_caption_max_similarity`` (max cosine to any other caption in the
    input; ``0`` when alone). The parent video gets
    ``repeated_caption_group_count``.

    Args:
        session: Database session.
        caption_sample_ids: Sample ids aligned with the indices in ``result``.
        video_sample_id: Parent video sample id.
        result: Output of :func:`find_repeated_captions`.
        caption_embeddings: Optional embeddings aligned with ``caption_sample_ids``
            used to write per-caption max similarity.
    """
    if len(caption_sample_ids) == 0:
        return

    group_id_by_index: dict[int, int] = {}
    for group in result.groups:
        for index in group.member_indices:
            group_id_by_index[index] = group.group_id

    max_similarity_by_index: dict[int, float] = {}
    if caption_embeddings is not None:
        if len(caption_embeddings) != len(caption_sample_ids):
            raise ValueError(
                f"caption_embeddings and caption_sample_ids must have the same "
                f"length, got {len(caption_embeddings)} and {len(caption_sample_ids)}."
            )
        max_similarity_by_index = _max_pairwise_similarities(
            embeddings=np.asarray(caption_embeddings, dtype=np.float32)
        )

    for index, sample_id in enumerate(caption_sample_ids):
        group_id = group_id_by_index.get(index)
        if group_id is not None:
            metadata_resolver.set_value_for_sample(
                session=session,
                sample_id=sample_id,
                key=REPEATED_CAPTION_GROUP_ID_KEY,
                value=group_id,
            )
        if index in max_similarity_by_index:
            metadata_resolver.set_value_for_sample(
                session=session,
                sample_id=sample_id,
                key=REPEATED_CAPTION_MAX_SIMILARITY_KEY,
                value=max_similarity_by_index[index],
            )

    metadata_resolver.set_value_for_sample(
        session=session,
        sample_id=video_sample_id,
        key=REPEATED_CAPTION_GROUP_COUNT_KEY,
        value=len(result.groups),
    )


def _validate_intervals(intervals: Sequence[tuple[float, float]]) -> None:
    for index, (start_time_s, end_time_s) in enumerate(intervals):
        if not (0.0 <= start_time_s < end_time_s):
            raise ValueError(
                f"Invalid interval at index {index}: "
                f"expected 0 <= start < end, got ({start_time_s}, {end_time_s})."
            )


def _pairwise_cosine_similarities(
    embeddings: NDArray[np.float32],
) -> NDArray[np.float32]:
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.maximum(norms, np.finfo(np.float32).tiny)
    normalized = embeddings / norms
    return normalized @ normalized.T


def _max_pairwise_similarities(embeddings: NDArray[np.float32]) -> dict[int, float]:
    if embeddings.shape[0] == 0:
        return {}
    if embeddings.shape[0] == 1:
        return {0: 0.0}

    similarity_matrix = _pairwise_cosine_similarities(embeddings=embeddings)
    np.fill_diagonal(similarity_matrix, -np.inf)
    max_per_row = similarity_matrix.max(axis=1)
    return {index: float(max_per_row[index]) for index in range(len(max_per_row))}


def _spans_are_separated(
    interval_a: tuple[float, float],
    interval_b: tuple[float, float],
    min_gap_s: float,
) -> bool:
    start_a, end_a = interval_a
    start_b, end_b = interval_b
    return end_a + min_gap_s <= start_b or end_b + min_gap_s <= start_a


def _collect_matches(
    similarity_matrix: NDArray[np.float32],
    intervals: Sequence[tuple[float, float]],
    similarity_threshold: float,
    min_gap_s: float,
) -> list[CaptionRepetitionMatch]:
    matches: list[CaptionRepetitionMatch] = []
    count = len(intervals)
    for index_a in range(count):
        for index_b in range(index_a + 1, count):
            similarity = float(similarity_matrix[index_a, index_b])
            if similarity < similarity_threshold:
                continue
            if not _spans_are_separated(
                interval_a=intervals[index_a],
                interval_b=intervals[index_b],
                min_gap_s=min_gap_s,
            ):
                continue
            matches.append(
                CaptionRepetitionMatch(
                    index_a=index_a,
                    index_b=index_b,
                    similarity=similarity,
                )
            )
    return matches


def _clique_groups(
    matches: Sequence[CaptionRepetitionMatch],
) -> list[CaptionRepetitionGroup]:
    """Build groups where every pair is a match (complete linkage / cliques).

    Grows greedily from strongest matches so a weak bridge cannot absorb an
    unrelated caption into an otherwise tight cluster. Each caption appears in
    at most one group.
    """
    if not matches:
        return []

    edge_set: set[tuple[int, int]] = set()
    for match in matches:
        edge_set.add(_edge_key(match.index_a, match.index_b))

    ordered_matches = sorted(matches, key=lambda match: match.similarity, reverse=True)
    assigned: set[int] = set()
    groups: list[CaptionRepetitionGroup] = []

    for match in ordered_matches:
        if match.index_a in assigned or match.index_b in assigned:
            continue

        clique = [match.index_a, match.index_b]
        assigned.add(match.index_a)
        assigned.add(match.index_b)

        candidates = sorted(
            {
                index
                for edge in edge_set
                for index in edge
                if index not in assigned
            }
        )
        for candidate in candidates:
            if _is_connected_to_all(candidate=candidate, members=clique, edge_set=edge_set):
                clique.append(candidate)
                assigned.add(candidate)

        groups.append(
            CaptionRepetitionGroup(
                group_id=len(groups),
                member_indices=tuple(sorted(clique)),
            )
        )

    return groups


def _edge_key(index_a: int, index_b: int) -> tuple[int, int]:
    return (index_a, index_b) if index_a < index_b else (index_b, index_a)


def _is_connected_to_all(
    candidate: int,
    members: Sequence[int],
    edge_set: set[tuple[int, int]],
) -> bool:
    return all(_edge_key(candidate, member) in edge_set for member in members)
