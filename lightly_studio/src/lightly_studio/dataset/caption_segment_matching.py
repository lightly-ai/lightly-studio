"""Score how well video segment embeddings match caption text embeddings.

Prototype helper: embeds each time interval with Perception Encoder (one video open)
and returns cosine similarities against provided caption embeddings. Callers typically
store each score on the caption sample as metadata under
``CAPTION_SEGMENT_MATCH_SCORE_KEY``, and video-level min/avg under
``MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY`` / ``AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY``.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.resolvers import metadata_resolver

CAPTION_SEGMENT_MATCH_SCORE_KEY = "caption_segment_match_score"
CAPTION_SEGMENT_MEAN_POOLED_SCORE_KEY = "caption_segment_mean_pooled_score"
CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY = "caption_segment_top2_match_score"
CAPTION_SEGMENT_HARD_NEGATIVE_SCORE_KEY = "caption_segment_hard_negative_score"
CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY = "caption_segment_alignment_margin"
MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY = "min_caption_segment_match_score"
AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY = "avg_caption_segment_match_score"
MIN_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY = "min_caption_segment_top2_match_score"
AVG_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY = "avg_caption_segment_top2_match_score"
MIN_CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY = "min_caption_segment_alignment_margin"
AVG_CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY = "avg_caption_segment_alignment_margin"
DEFAULT_TOP_K_FRAMES = 2
FRAME_EMBEDDING_NDIM = 3
CAPTION_EMBEDDING_NDIM = 2


@dataclass(frozen=True)
class CaptionSegmentFrameScores:
    """Aligned caption scores and same-video hard-negative comparisons.

    Attributes:
        mean_pooled_scores: Legacy scores from cosine similarity against mean-pooled
            frame embeddings.
        top_k_scores: Mean of the strongest ``top_k`` per-frame similarities.
        hard_negative_scores: Best top-k score among non-overlapping segments in the
            same video, or ``None`` when no candidate exists.
        alignment_margins: Aligned top-k score minus its hard-negative score, or
            ``None`` when no hard negative exists.
    """

    mean_pooled_scores: tuple[float, ...]
    top_k_scores: tuple[float, ...]
    hard_negative_scores: tuple[float | None, ...]
    alignment_margins: tuple[float | None, ...]


def score_caption_segments(
    video_path: str,
    intervals: Sequence[tuple[float, float]],
    caption_embeddings: Sequence[Sequence[float]],
    embedding_generator: PerceptionEncoderEmbeddingGenerator | None = None,
) -> list[float]:
    """Embed video intervals and score them against caption embeddings.

    Opens ``video_path`` once, samples frames in each interval, mean-pools with PE
    (same path as whole-video embeddings), and returns cosine similarity to each
    caption embedding. Same score meaning as text search: ``1 - cosine_distance``.

    Args:
        video_path: Path or URL of the video.
        intervals: ``(start_time_s, end_time_s)`` pairs with ``0 <= start < end``.
        caption_embeddings: Caption embedding vectors aligned with ``intervals``.
        embedding_generator: Optional PE generator; constructed if omitted.

    Returns:
        One similarity score per interval, in the same order as the inputs.

    Raises:
        ValueError: If the interval/embedding lists differ in length or an interval
            is invalid.
    """
    if len(intervals) != len(caption_embeddings):
        raise ValueError(
            f"intervals and caption_embeddings must have the same length, "
            f"got {len(intervals)} and {len(caption_embeddings)}."
        )
    if not intervals:
        return []

    generator = embedding_generator or PerceptionEncoderEmbeddingGenerator()
    segment_embeddings = generator.embed_video_segments(
        filepath=video_path,
        intervals=intervals,
    )
    caption_matrix = np.asarray(caption_embeddings, dtype=np.float32)
    return _cosine_similarities(
        segment_embeddings=segment_embeddings,
        caption_embeddings=caption_matrix,
    )


def score_caption_segment_frames(
    video_path: str,
    intervals: Sequence[tuple[float, float]],
    caption_embeddings: Sequence[Sequence[float]],
    embedding_generator: PerceptionEncoderEmbeddingGenerator | None = None,
    top_k: int = DEFAULT_TOP_K_FRAMES,
) -> CaptionSegmentFrameScores:
    """Score aligned captions using individual frames and same-video negatives.

    Args:
        video_path: Path or URL of the video.
        intervals: ``(start_time_s, end_time_s)`` pairs with ``0 <= start < end``.
        caption_embeddings: Caption embedding vectors aligned with ``intervals``.
        embedding_generator: Optional PE generator; constructed if omitted.
        top_k: Number of strongest per-frame similarities to average.

    Returns:
        Mean-pooled, top-k, hard-negative, and alignment-margin scores.

    Raises:
        ValueError: If inputs are inconsistent or ``top_k`` is invalid.
    """
    _validate_aligned_inputs(intervals=intervals, caption_embeddings=caption_embeddings)
    if not intervals:
        return CaptionSegmentFrameScores(
            mean_pooled_scores=(),
            top_k_scores=(),
            hard_negative_scores=(),
            alignment_margins=(),
        )

    generator = embedding_generator or PerceptionEncoderEmbeddingGenerator()
    frame_embeddings = generator.embed_video_segment_frames(
        filepath=video_path,
        intervals=intervals,
    )
    caption_matrix = np.asarray(caption_embeddings, dtype=np.float32)
    _validate_frame_embeddings(
        frame_embeddings=frame_embeddings,
        caption_embeddings=caption_matrix,
        segment_count=len(intervals),
        top_k=top_k,
    )
    mean_pooled_scores = _cosine_similarities(
        segment_embeddings=frame_embeddings.mean(axis=1),
        caption_embeddings=caption_matrix,
    )
    similarities = _get_caption_segment_frame_similarities(
        frame_embeddings=frame_embeddings,
        caption_embeddings=caption_matrix,
    )
    top_k_matrix = _mean_top_k(similarities=similarities, top_k=top_k)
    top_k_scores = np.diag(top_k_matrix).astype(np.float64).tolist()
    hard_negative_scores = _get_hard_negative_scores(
        top_k_matrix=top_k_matrix,
        intervals=intervals,
    )
    margins = _get_alignment_margins(
        aligned_scores=top_k_scores,
        hard_negative_scores=hard_negative_scores,
    )
    return CaptionSegmentFrameScores(
        mean_pooled_scores=tuple(mean_pooled_scores),
        top_k_scores=tuple(top_k_scores),
        hard_negative_scores=tuple(hard_negative_scores),
        alignment_margins=tuple(margins),
    )


def set_video_caption_match_aggregates(
    session: Session,
    video_sample_id: UUID,
    scores: Sequence[float],
) -> None:
    """Write min/avg caption-segment match scores onto the parent video sample.

    No-op when ``scores`` is empty so videos without scored captions keep no key
    (they sort last and are excluded by a Low-match filter).

    Args:
        session: Database session.
        video_sample_id: Sample id of the parent video.
        scores: Per-caption match scores already written on caption samples.
    """
    if not scores:
        return

    metadata_resolver.set_value_for_sample(
        session=session,
        sample_id=video_sample_id,
        key=MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        value=float(min(scores)),
    )
    metadata_resolver.set_value_for_sample(
        session=session,
        sample_id=video_sample_id,
        key=AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY,
        value=float(sum(scores) / len(scores)),
    )


def set_video_caption_frame_score_aggregates(
    session: Session,
    video_sample_id: UUID,
    scores: CaptionSegmentFrameScores,
) -> None:
    """Write top-k and alignment-margin aggregates onto a video sample.

    Args:
        session: The database session.
        video_sample_id: The ID of the parent video sample.
        scores: Frame-level caption matching scores for the video.
    """
    if not scores.top_k_scores:
        return

    metadata = {
        MIN_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY: min(scores.top_k_scores),
        AVG_CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY: _mean(scores.top_k_scores),
    }
    margins = [margin for margin in scores.alignment_margins if margin is not None]
    if margins:
        metadata[MIN_CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY] = min(margins)
        metadata[AVG_CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY] = _mean(margins)
    metadata_resolver.bulk_update_metadata(
        session,
        [(video_sample_id, metadata)],
    )


def _cosine_similarities(
    segment_embeddings: NDArray[np.float32],
    caption_embeddings: NDArray[np.float32],
) -> list[float]:
    """Return per-row cosine similarity (equivalent to ``1 - cosine_distance``)."""
    segment_norms = np.linalg.norm(segment_embeddings, axis=1, keepdims=True)
    caption_norms = np.linalg.norm(caption_embeddings, axis=1, keepdims=True)
    # Avoid division by zero for empty/degenerate vectors.
    segment_norms = np.maximum(segment_norms, np.finfo(np.float32).tiny)
    caption_norms = np.maximum(caption_norms, np.finfo(np.float32).tiny)
    segment_normalized = segment_embeddings / segment_norms
    caption_normalized = caption_embeddings / caption_norms
    scores: list[float] = (
        (segment_normalized * caption_normalized).sum(axis=1).astype(np.float64).tolist()
    )
    return scores


def _validate_aligned_inputs(
    intervals: Sequence[tuple[float, float]],
    caption_embeddings: Sequence[Sequence[float]],
) -> None:
    if len(intervals) != len(caption_embeddings):
        raise ValueError(
            f"intervals and caption_embeddings must have the same length, "
            f"got {len(intervals)} and {len(caption_embeddings)}."
        )
    for index, (start_time_s, end_time_s) in enumerate(intervals):
        if not (0.0 <= start_time_s < end_time_s):
            raise ValueError(
                f"Invalid interval at index {index}: "
                f"expected 0 <= start < end, got ({start_time_s}, {end_time_s})."
            )


def _validate_frame_embeddings(
    frame_embeddings: NDArray[np.float32],
    caption_embeddings: NDArray[np.float32],
    segment_count: int,
    top_k: int,
) -> None:
    if frame_embeddings.ndim != FRAME_EMBEDDING_NDIM or frame_embeddings.shape[0] != segment_count:
        raise ValueError(
            "frame_embeddings must have shape (segments, frames, embedding_dimension)."
        )
    frame_count = frame_embeddings.shape[1]
    if not 1 <= top_k <= frame_count:
        raise ValueError(f"top_k must be in [1, {frame_count}], got {top_k}.")
    if (
        caption_embeddings.ndim != CAPTION_EMBEDDING_NDIM
        or caption_embeddings.shape[1] != frame_embeddings.shape[2]
    ):
        raise ValueError("Caption and frame embedding dimensions must match.")


def _get_caption_segment_frame_similarities(
    frame_embeddings: NDArray[np.float32],
    caption_embeddings: NDArray[np.float32],
) -> NDArray[np.float32]:
    frame_norms = np.linalg.norm(frame_embeddings, axis=2, keepdims=True)
    caption_norms = np.linalg.norm(caption_embeddings, axis=1, keepdims=True)
    normalized_frames = frame_embeddings / np.maximum(frame_norms, np.finfo(np.float32).tiny)
    normalized_captions = caption_embeddings / np.maximum(caption_norms, np.finfo(np.float32).tiny)
    return np.asarray(
        np.einsum("sfd,cd->csf", normalized_frames, normalized_captions),
        dtype=np.float32,
    )


def _mean_top_k(
    similarities: NDArray[np.float32],
    top_k: int,
) -> NDArray[np.float32]:
    frame_count = similarities.shape[2]
    partitioned = np.partition(similarities, kth=frame_count - top_k, axis=2)
    return np.asarray(partitioned[:, :, -top_k:].mean(axis=2), dtype=np.float32)


def _get_hard_negative_scores(
    top_k_matrix: NDArray[np.float32],
    intervals: Sequence[tuple[float, float]],
) -> list[float | None]:
    scores: list[float | None] = []
    for caption_index, caption_interval in enumerate(intervals):
        candidates = [
            float(top_k_matrix[caption_index, segment_index])
            for segment_index, segment_interval in enumerate(intervals)
            if segment_index != caption_index
            and _intervals_are_separated(caption_interval, segment_interval)
        ]
        scores.append(max(candidates) if candidates else None)
    return scores


def _get_alignment_margins(
    aligned_scores: Sequence[float],
    hard_negative_scores: Sequence[float | None],
) -> list[float | None]:
    return [
        None if negative is None else aligned - negative
        for aligned, negative in zip(aligned_scores, hard_negative_scores)
    ]


def _intervals_are_separated(
    interval_a: tuple[float, float],
    interval_b: tuple[float, float],
) -> bool:
    start_a, end_a = interval_a
    start_b, end_b = interval_b
    return end_a <= start_b or end_b <= start_a


def _mean(values: Sequence[float]) -> float:
    return float(sum(values) / len(values))
