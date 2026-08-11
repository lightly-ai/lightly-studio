"""Helpers for creating, scoring, and summarizing timed video captions."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlmodel import Session

from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.dataset.caption_repetition import (
    DEFAULT_SIMILARITY_THRESHOLD,
    REPEATED_CAPTION_GROUP_ID_KEY,
    REPEATED_CAPTION_MAX_SIMILARITY_KEY,
    find_repeated_captions,
    write_caption_repetition_metadata,
)
from lightly_studio.dataset.caption_segment_matching import CAPTION_SEGMENT_MATCH_SCORE_KEY
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.dataset.video_seek_pass import score_quality_and_caption_segments
from lightly_studio.models.caption import CaptionCreate, CaptionTable
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    caption_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
)


def add_captions_from_annotations(video: VideoSample) -> list[UUID]:
    """Mirror the annotations of a video as captions with the same temporal spans.

    Annotations without a temporal span are mirrored as captions without a span.

    Args:
        video: The video sample whose annotations are mirrored.

    Returns:
        Created caption sample IDs, ordered by start time.
    """
    captions: list[CaptionCreate] = []
    for annotation in video.annotations:
        span = annotation.annotation_base.temporal_span_details
        captions.append(
            CaptionCreate(
                parent_sample_id=video.sample_id,
                text=annotation.class_name,
                start_time_s=span.start_time_s if span is not None else None,
                end_time_s=span.end_time_s if span is not None else None,
            )
        )
    captions.sort(key=lambda caption: caption.start_time_s if caption.start_time_s else 0.0)
    return caption_resolver.create_many(
        session=video.get_object_session(),
        parent_collection_id=video.collection_id,
        captions=captions,
    )


def add_captions_from_sentences(video: VideoSample, sentences_path: Path) -> list[UUID]:
    """Create timed captions for a video from a sentences JSON file.

    Expected JSON shape::

        {
          "sentences": [
            {"text": "...", "start": 1.86, "end": 4.1},
            ...
          ]
        }

    Args:
        video: The video sample to attach captions to.
        sentences_path: Path to the sentences JSON file.

    Returns:
        Created caption sample IDs, ordered by start time.
    """
    payload = json.loads(sentences_path.read_text(encoding="utf-8"))
    sentences = payload["sentences"]
    captions = [
        CaptionCreate(
            parent_sample_id=video.sample_id,
            text=sentence["text"],
            start_time_s=float(sentence["start"]),
            end_time_s=float(sentence["end"]),
        )
        for sentence in sentences
    ]
    captions.sort(key=lambda caption: caption.start_time_s if caption.start_time_s else 0.0)
    return caption_resolver.create_many(
        session=video.get_object_session(),
        parent_collection_id=video.collection_id,
        captions=captions,
    )


def score_timed_captions_for_video(  # noqa: PLR0913
    video: VideoSample,
    caption_ids: Sequence[UUID],
    *,
    embedding_generator: PerceptionEncoderEmbeddingGenerator | None = None,
    compute_quality: bool = True,
    embed_video: bool = False,
    interval_buffer_ratio: float = 0.0,
) -> None:
    """Score timed captions (and optionally quality / video embed) in one video open.

    Args:
        video: Parent video sample.
        caption_ids: Caption sample IDs belonging to ``video``.
        embedding_generator: Optional PE generator; uses the default when omitted.
        compute_quality: If True, compute and store video quality metadata.
        embed_video: If True, embed and store a whole-video PE vector.
        interval_buffer_ratio: Fraction of each caption duration to expand on both
            sides when sampling segment embeddings (e.g. ``0.1`` = ±10%).
    """
    session = video.get_object_session()
    timed = _timed_captions(session=session, caption_ids=caption_ids)
    if not timed and not compute_quality and not embed_video:
        return

    scored = _timed_captions_with_embeddings(
        session=session,
        video=video,
        timed=timed,
        interval_buffer_ratio=interval_buffer_ratio,
    )
    if not scored.caption_ids and not compute_quality and not embed_video:
        return

    score_quality_and_caption_segments(
        session=session,
        video_sample_id=video.sample_id,
        video_path=video.file_path_abs,
        video_collection_id=video.collection_id,
        caption_sample_ids=scored.caption_ids,
        intervals=scored.intervals,
        caption_embeddings=scored.embeddings,
        compute_quality=compute_quality,
        embed_full_video=embed_video,
        embedding_generator=embedding_generator,
    )


def detect_repeated_captions_for_video(
    video: VideoSample,
    caption_ids: Sequence[UUID],
    *,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    min_gap_s: float = 0.0,
) -> None:
    """Cluster temporally separated captions with similar text embeddings."""
    session = video.get_object_session()
    timed = _timed_captions(session=session, caption_ids=caption_ids)
    if len(timed) < 2:  # noqa: PLR2004
        return

    scored = _timed_captions_with_embeddings(
        session=session,
        video=video,
        timed=timed,
        interval_buffer_ratio=0.0,
    )
    if len(scored.intervals) < 2:  # noqa: PLR2004
        return

    result = find_repeated_captions(
        caption_embeddings=scored.embeddings,
        intervals=scored.intervals,
        similarity_threshold=similarity_threshold,
        min_gap_s=min_gap_s,
    )
    write_caption_repetition_metadata(
        session=session,
        caption_sample_ids=scored.caption_ids,
        video_sample_id=video.sample_id,
        result=result,
        caption_embeddings=scored.embeddings,
    )


def print_timed_captions_summary(
    session: Session,
    video: VideoSample,
    caption_ids: Sequence[UUID],
) -> None:
    """Print timed captions with match and repetition metadata for one video."""
    captions = caption_resolver.get_by_ids(session=session, sample_ids=list(caption_ids))
    print(f"{video.file_name} ({video.duration_s}s): {len(captions)} caption(s)")
    for caption in captions:
        span = caption.temporal_span_details
        time_range = (
            f"{span.start_time_s:.2f}s - {span.end_time_s:.2f}s" if span is not None else "no span"
        )
        extras: list[str] = []
        if span is not None:
            match_score = metadata_resolver.get_value_for_sample(
                session=session,
                sample_id=caption.sample_id,
                key=CAPTION_SEGMENT_MATCH_SCORE_KEY,
            )
            group_id = metadata_resolver.get_value_for_sample(
                session=session,
                sample_id=caption.sample_id,
                key=REPEATED_CAPTION_GROUP_ID_KEY,
            )
            max_sim = metadata_resolver.get_value_for_sample(
                session=session,
                sample_id=caption.sample_id,
                key=REPEATED_CAPTION_MAX_SIMILARITY_KEY,
            )
            if match_score is not None:
                extras.append(f"match={match_score:.3f}")
            if group_id is not None:
                extras.append(f"repeat_group={group_id}")
            if max_sim is not None:
                extras.append(f"max_sim={max_sim:.3f}")
        extra_text = f", {', '.join(extras)}" if extras else ""
        print(f"  - [{time_range}] {caption.text}{extra_text}")


@dataclass(frozen=True)
class _TimedCaptionEmbeddings:
    """Aligned caption ids, intervals, and embeddings for timed captions."""

    caption_ids: list[UUID]
    intervals: list[tuple[float, float]]
    embeddings: list[list[float]]


def _timed_captions(session: Session, caption_ids: Sequence[UUID]) -> list[CaptionTable]:
    captions = caption_resolver.get_by_ids(session=session, sample_ids=list(caption_ids))
    return [caption for caption in captions if caption.temporal_span_details is not None]


def _timed_captions_with_embeddings(
    session: Session,
    video: VideoSample,
    timed: Sequence[CaptionTable],
    *,
    interval_buffer_ratio: float,
) -> _TimedCaptionEmbeddings:
    if not timed:
        return _TimedCaptionEmbeddings(caption_ids=[], intervals=[], embeddings=[])

    caption_collection_id = collection_resolver.get_by_name(
        session=session,
        name=SampleType.CAPTION.value.lower(),
        parent_collection_id=video.collection_id,
    )
    if caption_collection_id is None:
        raise ValueError(f"Caption collection not found for video {video.sample_id}.")

    model_id = EmbeddingManagerProvider.get_embedding_manager().load_or_get_default_model(
        session=session,
        collection_id=caption_collection_id,
    )
    if model_id is None:
        raise ValueError("No embedding model available for caption embeddings.")

    timed_ids = [caption.sample_id for caption in timed]
    embedding_rows = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=timed_ids,
        embedding_model_id=model_id,
    )
    embedding_by_id = {row.sample_id: row.embedding for row in embedding_rows}

    intervals: list[tuple[float, float]] = []
    caption_embeddings: list[list[float]] = []
    scored_ids: list[UUID] = []
    for caption in timed:
        embedding = embedding_by_id.get(caption.sample_id)
        span = caption.temporal_span_details
        if embedding is None or span is None:
            continue
        start_time_s, end_time_s = _buffered_interval(
            start_time_s=span.start_time_s,
            end_time_s=span.end_time_s,
            buffer_ratio=interval_buffer_ratio,
        )
        intervals.append((start_time_s, end_time_s))
        caption_embeddings.append(list(embedding))
        scored_ids.append(caption.sample_id)

    return _TimedCaptionEmbeddings(
        caption_ids=scored_ids,
        intervals=intervals,
        embeddings=caption_embeddings,
    )


def _buffered_interval(
    *,
    start_time_s: float,
    end_time_s: float,
    buffer_ratio: float,
) -> tuple[float, float]:
    if buffer_ratio <= 0.0:
        return start_time_s, end_time_s
    duration = end_time_s - start_time_s
    buffer = buffer_ratio * duration
    return max(0.0, start_time_s - buffer), end_time_s + buffer
