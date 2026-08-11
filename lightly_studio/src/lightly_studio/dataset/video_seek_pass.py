"""Run quality scoring and PE segment embedding in a single video open.

Seek-sampling workloads (quality frames, shake bursts, whole-video embed, caption
intervals) share one ``fsspec`` open so remote videos are not fetched repeatedly.
``add_videos`` full sequential decode remains a separate pass.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlmodel import Session

from lightly_studio.dataset.caption_segment_matching import (
    CAPTION_SEGMENT_MATCH_SCORE_KEY,
    cosine_similarities,
    set_video_caption_match_aggregates,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.dataset.video_frame_io import open_video_container
from lightly_studio.dataset.video_quality import (
    DEFAULT_MAX_EDGE,
    DEFAULT_NUM_FRAMES,
    ShakeSamplingConfig,
    VideoQualityScores,
    score_opened_video_quality,
    set_video_quality_metadata,
)
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import metadata_resolver, sample_embedding_resolver


@dataclass(frozen=True)
class VideoSeekPassResult:
    """Outputs from a single seek pass over one video."""

    quality_scores: VideoQualityScores | None
    """Quality aggregates when ``compute_quality`` was requested."""

    segment_embeddings: NDArray[np.float32] | None
    """PE embeddings for ``segment_intervals``, shape ``(N, dim)``."""

    full_video_embedding: NDArray[np.float32] | None
    """Whole-video PE embedding when ``embed_full_video`` was requested."""


def run_video_seek_pass(  # noqa: PLR0913
    filepath: str,
    *,
    compute_quality: bool = False,
    embed_full_video: bool = False,
    segment_intervals: Sequence[tuple[float, float]] | None = None,
    embedding_generator: PerceptionEncoderEmbeddingGenerator | None = None,
    quality_num_frames: int = DEFAULT_NUM_FRAMES,
    quality_max_edge: int = DEFAULT_MAX_EDGE,
    shake_sampling: ShakeSamplingConfig | None = None,
) -> VideoSeekPassResult:
    """Open ``filepath`` once and optionally compute quality + PE embeddings.

    Args:
        filepath: Local path or fsspec URL of the video.
        compute_quality: If True, score blur/lighting/motion/shake.
        embed_full_video: If True, embed the full video duration with PE.
        segment_intervals: Optional caption (or other) time ranges to embed.
        embedding_generator: PE generator; constructed if embeddings are needed
            and this is omitted.
        quality_num_frames: Uniform frames for blur/lighting/motion.
        quality_max_edge: Max edge length for quality frame resize.
        shake_sampling: Dense-burst config for shake scoring.

    Returns:
        ``VideoSeekPassResult`` with the requested outputs (others ``None``).

    Raises:
        ValueError: If quality sampling args or intervals are invalid.
        MissingInputFileError: If the video path does not resolve.
        BrokenInputFileError: If the video cannot be decoded.
    """
    intervals = list(segment_intervals) if segment_intervals else []
    needs_embeddings = embed_full_video or bool(intervals)
    generator = (
        embedding_generator
        if not needs_embeddings
        else (embedding_generator or PerceptionEncoderEmbeddingGenerator())
    )

    with open_video_container(filepath) as opened:
        quality_scores = (
            score_opened_video_quality(
                opened=opened,
                num_frames=quality_num_frames,
                max_edge=quality_max_edge,
                shake_sampling=shake_sampling,
            )
            if compute_quality
            else None
        )

        if not needs_embeddings:
            return VideoSeekPassResult(
                quality_scores=quality_scores,
                segment_embeddings=None,
                full_video_embedding=None,
            )

        assert generator is not None
        embed_intervals: list[tuple[float, float]] = []
        if embed_full_video:
            embed_intervals.append((0.0, opened.duration_s))
        embed_intervals.extend(intervals)

        all_embeddings = generator.embed_opened_video_segments(
            opened=opened,
            intervals=embed_intervals,
        )
        if embed_full_video:
            full_video_embedding = all_embeddings[0]
            segment_embeddings = all_embeddings[1:] if intervals else None
        else:
            full_video_embedding = None
            segment_embeddings = all_embeddings if intervals else None

        return VideoSeekPassResult(
            quality_scores=quality_scores,
            segment_embeddings=segment_embeddings,
            full_video_embedding=full_video_embedding,
        )


def score_quality_and_caption_segments(  # noqa: PLR0913
    session: Session,
    *,
    video_sample_id: UUID,
    video_path: str,
    video_collection_id: UUID,
    caption_sample_ids: Sequence[UUID],
    intervals: Sequence[tuple[float, float]],
    caption_embeddings: Sequence[Sequence[float]],
    compute_quality: bool = True,
    embed_full_video: bool = False,
    embedding_generator: PerceptionEncoderEmbeddingGenerator | None = None,
    quality_num_frames: int = DEFAULT_NUM_FRAMES,
    quality_max_edge: int = DEFAULT_MAX_EDGE,
) -> list[float]:
    """Score quality and caption segments in one open; persist results.

    Caption text embeddings must already exist. Opens ``video_path`` once to
    optionally write quality metadata, optionally store a whole-video embedding,
    and write per-caption match scores plus video min/avg aggregates.

    Args:
        session: Database session.
        video_sample_id: Parent video sample id.
        video_path: Local path or fsspec URL of the video.
        video_collection_id: Video collection id (for embedding model lookup).
        caption_sample_ids: Caption sample ids aligned with ``intervals``.
        intervals: Buffered or raw caption time ranges.
        caption_embeddings: Caption embedding vectors aligned with ``intervals``.
        compute_quality: If True, compute and store quality metadata.
        embed_full_video: If True, embed and store a whole-video PE vector.
        embedding_generator: Optional PE generator.
        quality_num_frames: Uniform frames for quality scoring.
        quality_max_edge: Max edge for quality frame resize.

    Returns:
        Per-caption match scores in the same order as ``intervals``.

    Raises:
        ValueError: If interval/caption/embedding lists differ in length.
    """
    if not (len(intervals) == len(caption_embeddings) == len(caption_sample_ids)):
        raise ValueError(
            "caption_sample_ids, intervals, and caption_embeddings must have the same "
            f"length, got {len(caption_sample_ids)}, {len(intervals)}, "
            f"and {len(caption_embeddings)}."
        )

    if not intervals and not compute_quality and not embed_full_video:
        return []

    result = run_video_seek_pass(
        filepath=video_path,
        compute_quality=compute_quality,
        embed_full_video=embed_full_video,
        segment_intervals=intervals if intervals else None,
        embedding_generator=embedding_generator,
        quality_num_frames=quality_num_frames,
        quality_max_edge=quality_max_edge,
    )

    if result.quality_scores is not None:
        set_video_quality_metadata(
            session=session,
            video_sample_id=video_sample_id,
            scores=result.quality_scores,
        )

    if result.full_video_embedding is not None:
        _store_single_video_embedding(
            session=session,
            video_collection_id=video_collection_id,
            video_sample_id=video_sample_id,
            embedding=result.full_video_embedding,
        )

    if not intervals:
        return []

    assert result.segment_embeddings is not None
    caption_matrix = np.asarray(caption_embeddings, dtype=np.float32)
    scores = cosine_similarities(
        segment_embeddings=result.segment_embeddings,
        caption_embeddings=caption_matrix,
    )
    for caption_id, score in zip(caption_sample_ids, scores):
        metadata_resolver.set_value_for_sample(
            session=session,
            sample_id=caption_id,
            key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            value=score,
        )
    set_video_caption_match_aggregates(
        session=session,
        video_sample_id=video_sample_id,
        scores=scores,
    )
    return scores


def _store_single_video_embedding(
    session: Session,
    video_collection_id: UUID,
    video_sample_id: UUID,
    embedding: NDArray[np.float32],
) -> None:
    """Persist one whole-video embedding using the collection default model."""
    embedding_manager = EmbeddingManagerProvider.get_embedding_manager()
    model_id = embedding_manager.load_or_get_default_model(
        session=session,
        collection_id=video_collection_id,
    )
    if model_id is None:
        return
    sample_embedding_resolver.create_many(
        session=session,
        sample_embeddings=[
            SampleEmbeddingCreate(
                sample_id=video_sample_id,
                embedding_model_id=model_id,
                embedding=embedding,
            )
        ],
    )
