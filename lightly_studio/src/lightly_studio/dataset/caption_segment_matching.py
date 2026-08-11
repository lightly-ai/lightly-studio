"""Score how well video segment embeddings match caption text embeddings.

Prototype helper: embeds each time interval with Perception Encoder (one video open)
and returns cosine similarities against provided caption embeddings. Callers typically
store each score on the caption sample as metadata under
``CAPTION_SEGMENT_MATCH_SCORE_KEY``, and video-level min/avg under
``MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY`` / ``AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY``.
"""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.resolvers import metadata_resolver

CAPTION_SEGMENT_MATCH_SCORE_KEY = "caption_segment_match_score"
MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY = "min_caption_segment_match_score"
AVG_CAPTION_SEGMENT_MATCH_SCORE_KEY = "avg_caption_segment_match_score"


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
    return cosine_similarities(
        segment_embeddings=segment_embeddings,
        caption_embeddings=caption_matrix,
    )


def set_video_caption_match_aggregates(
    session: Session,
    video_sample_id: UUID,
    scores: Sequence[float],
) -> None:
    """Write min/avg caption–segment match scores onto the parent video sample.

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


def cosine_similarities(
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
