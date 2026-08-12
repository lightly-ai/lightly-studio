"""Transcribe egocentric videos, compute QA signals, and launch LightlyStudio."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import (
    caption_embedding,
    caption_repetition,
    caption_segment_matching,
    whisper_transcript,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    SUPPORTED_MODEL_NAMES,
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.dataset.whisper_transcript import ActionPhraseSettings, CaptionUnit
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.models.collection import SampleType
from lightly_studio.resolvers import (
    caption_resolver,
    collection_resolver,
    metadata_resolver,
    sample_embedding_resolver,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VIDEOS_PATH = REPOSITORY_ROOT / "test" / "data"
DEFAULT_WHISPER_PYTHON = REPOSITORY_ROOT / "test" / "whisper-env" / "bin" / "python"
DEFAULT_TRANSCRIPT_CACHE = REPOSITORY_ROOT / "test" / "transcripts"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "egocentric_qa.db"
WHISPER_WORKER_PATH = PROJECT_ROOT / "scripts" / "transcribe_with_faster_whisper.py"
LOW_CAPTION_MATCH_MAX = 0.35
MIN_CAPTIONS_FOR_REPETITION = 2
MIN_NARRATION_WORDS_PER_MINUTE = 25.0
CaptionMatchScoring = Literal["mean_pool", "top2"]


@dataclass(frozen=True)
class CaptionEmbeddingBatch:
    """Timed captions and aligned embedding data for one video."""

    caption_sample_ids: tuple[UUID, ...]
    intervals: tuple[tuple[float, float], ...]
    embeddings: tuple[tuple[float, ...], ...]


def run_pipeline(args: argparse.Namespace) -> None:
    """Run transcription, QA scoring, and visualization.

    Args:
        args: Parsed command-line arguments.
    """
    videos_path = args.videos.resolve()
    video_paths = _find_videos(videos_path=videos_path)
    transcript_paths = _ensure_transcripts(video_paths=video_paths, args=args)

    db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=True)
    dataset = VideoDataset.create(name="egocentric-qa")
    dataset.add_videos_from_path(path=videos_path, embed=False, embed_frames=False)
    dataset.compute_quality_scores()

    embedding_generator = PerceptionEncoderEmbeddingGenerator(model_name=args.pe_model)
    ls.set_default_embedding_model(embedding_generator)
    captions_by_video = _create_transcript_captions(
        dataset=dataset,
        transcript_paths=transcript_paths,
        caption_unit=args.caption_unit,
        action_phrase_settings=ActionPhraseSettings(
            pause_threshold_s=args.action_pause_s,
            window_padding_s=args.action_window_padding_s,
            min_window_duration_s=args.action_min_window_s,
            max_words=args.action_max_words,
        ),
    )
    all_caption_ids = [
        caption_id for _, caption_ids in captions_by_video for caption_id in caption_ids
    ]
    caption_embedding.embed_captions(
        session=dataset.session,
        caption_sample_ids=all_caption_ids,
    )

    frame_score_batches = []
    for video, caption_ids in captions_by_video:
        batch = _get_caption_embedding_batch(video=video, caption_ids=caption_ids)
        frame_scores = _score_caption_matches(
            video=video,
            batch=batch,
            embedding_generator=embedding_generator,
            primary_scoring=args.caption_match_scoring,
        )
        if frame_scores is not None:
            frame_score_batches.append(frame_scores)
        _detect_repeated_captions(video=video, batch=batch)
        _write_qa_summary(
            video=video,
            include_legacy_caption_threshold=args.caption_match_scoring == "mean_pool",
        )

    _print_caption_match_summary(
        score_batches=frame_score_batches,
        primary_scoring=args.caption_match_scoring,
    )
    print(f"Indexed {len(video_paths)} video(s) in {args.db_file.resolve()}.")
    if not args.no_gui:
        ls.start_gui(host=args.host, port=args.port)


def _find_videos(videos_path: Path) -> list[Path]:
    if not videos_path.is_dir():
        raise FileNotFoundError(f"Video directory does not exist: '{videos_path}'.")
    video_paths = sorted(path.resolve() for path in videos_path.rglob("*.mp4"))
    if not video_paths:
        raise FileNotFoundError(f"No MP4 videos found under: '{videos_path}'.")
    return video_paths


def _ensure_transcripts(
    video_paths: list[Path],
    args: argparse.Namespace,
) -> dict[Path, Path]:
    cache_dir = args.transcript_cache.resolve()
    cache_dir.mkdir(parents=True, exist_ok=True)
    transcription_config = (
        f"{args.whisper_model}|{args.whisper_beam_size}|{not args.disable_vad}|"
        f"{args.vad_threshold}|{args.vad_min_silence_ms}"
    )
    transcript_paths = {
        video: _get_transcript_path(
            video=video,
            cache_dir=cache_dir,
            transcription_config=transcription_config,
        )
        for video in video_paths
    }
    missing = [
        video
        for video in video_paths
        if args.force_transcribe or not transcript_paths[video].is_file()
    ]
    if not missing:
        print(f"Using {len(video_paths)} cached Whisper transcript(s) from {cache_dir}.")
        return transcript_paths

    # Keep the virtual environment's Python symlink intact so it can find its packages.
    whisper_python = args.whisper_python.absolute()
    if not whisper_python.is_file():
        raise FileNotFoundError(f"Whisper Python executable does not exist: '{whisper_python}'.")

    jobs_path = cache_dir / "whisper_jobs.json"
    jobs = [
        {
            "video_path": str(video),
            "output_path": str(transcript_paths[video]),
        }
        for video in missing
    ]
    jobs_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
    command = [
        str(whisper_python),
        str(WHISPER_WORKER_PATH),
        "--jobs",
        str(jobs_path),
        "--model",
        args.whisper_model,
        "--device",
        args.whisper_device,
        "--compute-type",
        args.whisper_compute_type,
        "--beam-size",
        str(args.whisper_beam_size),
        "--vad-threshold",
        str(args.vad_threshold),
        "--vad-min-silence-ms",
        str(args.vad_min_silence_ms),
    ]
    if args.disable_vad:
        command.append("--disable-vad")
    subprocess.run(command, check=True)
    return transcript_paths


def _get_transcript_path(video: Path, cache_dir: Path, transcription_config: str) -> Path:
    cache_key = f"{video}|{transcription_config}"
    path_hash = hashlib.sha256(cache_key.encode()).hexdigest()[:10]
    return cache_dir / f"{video.stem}.{path_hash}.faster-whisper.json"


def _create_transcript_captions(
    dataset: VideoDataset,
    transcript_paths: dict[Path, Path],
    caption_unit: CaptionUnit,
    action_phrase_settings: ActionPhraseSettings,
) -> list[tuple[VideoSample, list[UUID]]]:
    captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
    video_metadata: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in dataset:
        transcript_path = transcript_paths[Path(video.file_path_abs).resolve()]
        video_duration_s = float(video.duration_s) if video.duration_s is not None else None
        transcript = whisper_transcript.load_whisper_transcript(
            transcript_path,
            caption_unit=caption_unit,
            video_duration_s=video_duration_s,
            action_phrase_settings=action_phrase_settings,
        )
        words_per_minute = transcript.words_per_minute(duration_s=video_duration_s)
        captions = [
            CaptionCreate(
                parent_sample_id=video.sample_id,
                text=caption.text,
                start_time_s=caption.start_time_s,
                end_time_s=caption.end_time_s,
            )
            for caption in transcript.captions
        ]
        caption_ids = caption_resolver.create_many(
            session=dataset.session,
            parent_collection_id=video.collection_id,
            captions=captions,
        )
        captions_by_video.append((video, caption_ids))
        video_metadata.append(
            (
                video.sample_id,
                {
                    "whisper_language": transcript.language,
                    "whisper_language_probability": transcript.language_probability,
                    "whisper_word_count": transcript.word_count,
                    "whisper_words_per_minute": words_per_minute,
                    "whisper_wpm_pass": (
                        words_per_minute >= MIN_NARRATION_WORDS_PER_MINUTE
                        if words_per_minute is not None
                        else False
                    ),
                    "whisper_caption_count": len(caption_ids),
                    "whisper_caption_unit": caption_unit,
                    "whisper_speech_duration_s": transcript.speech_duration_s,
                    "whisper_silence_duration_s": transcript.silence_duration_s,
                    "whisper_silence_ratio": transcript.silence_ratio,
                    "whisper_silence_count": len(transcript.silences),
                    "expected_quality_label": _infer_expected_label(video.file_name),
                },
            )
        )
    metadata_resolver.bulk_update_metadata(dataset.session, video_metadata)
    return captions_by_video


def _get_caption_embedding_batch(
    video: VideoSample,
    caption_ids: list[UUID],
) -> CaptionEmbeddingBatch:
    session = video.get_object_session()
    caption_collection_id = collection_resolver.get_by_name(
        session=session,
        name=SampleType.CAPTION.value.lower(),
        parent_collection_id=video.collection_id,
    )
    if caption_collection_id is None or not caption_ids:
        return CaptionEmbeddingBatch(caption_sample_ids=(), intervals=(), embeddings=())

    model_id = EmbeddingManagerProvider.get_embedding_manager().load_or_get_default_model(
        session=session,
        collection_id=caption_collection_id,
    )
    if model_id is None:
        return CaptionEmbeddingBatch(caption_sample_ids=(), intervals=(), embeddings=())

    captions = caption_resolver.get_by_ids(session=session, sample_ids=caption_ids)
    embedding_rows = sample_embedding_resolver.get_by_sample_ids(
        session=session,
        sample_ids=caption_ids,
        embedding_model_id=model_id,
    )
    embedding_by_id = {row.sample_id: row.embedding for row in embedding_rows}
    aligned_ids = []
    intervals = []
    embeddings = []
    for caption in captions:
        span = caption.temporal_span_details
        embedding = embedding_by_id.get(caption.sample_id)
        if span is None or embedding is None:
            continue
        aligned_ids.append(caption.sample_id)
        intervals.append((span.start_time_s, span.end_time_s))
        embeddings.append(tuple(embedding))
    return CaptionEmbeddingBatch(
        caption_sample_ids=tuple(aligned_ids),
        intervals=tuple(intervals),
        embeddings=tuple(embeddings),
    )


def _score_caption_matches(
    video: VideoSample,
    batch: CaptionEmbeddingBatch,
    embedding_generator: PerceptionEncoderEmbeddingGenerator,
    primary_scoring: CaptionMatchScoring,
) -> caption_segment_matching.CaptionSegmentFrameScores | None:
    if not batch.intervals:
        return None
    scores = caption_segment_matching.score_caption_segment_frames(
        video_path=video.file_path_abs,
        intervals=batch.intervals,
        caption_embeddings=batch.embeddings,
        embedding_generator=embedding_generator,
    )
    session = video.get_object_session()
    primary_scores = (
        scores.mean_pooled_scores if primary_scoring == "mean_pool" else scores.top_k_scores
    )
    metadata_updates: list[tuple[UUID, Mapping[str, Any]]] = []
    score_rows = zip(
        batch.caption_sample_ids,
        primary_scores,
        scores.mean_pooled_scores,
        scores.top_k_scores,
        scores.hard_negative_scores,
        scores.alignment_margins,
    )
    for caption_id, primary_score, mean_score, top_k_score, negative_score, margin in score_rows:
        metadata = {
            caption_segment_matching.CAPTION_SEGMENT_MATCH_SCORE_KEY: primary_score,
            caption_segment_matching.CAPTION_SEGMENT_MEAN_POOLED_SCORE_KEY: mean_score,
            caption_segment_matching.CAPTION_SEGMENT_TOP_K_MATCH_SCORE_KEY: top_k_score,
        }
        if negative_score is not None:
            metadata[caption_segment_matching.CAPTION_SEGMENT_HARD_NEGATIVE_SCORE_KEY] = (
                negative_score
            )
        if margin is not None:
            metadata[caption_segment_matching.CAPTION_SEGMENT_ALIGNMENT_MARGIN_KEY] = margin
        metadata_updates.append((caption_id, metadata))
    metadata_resolver.bulk_update_metadata(
        session,
        metadata_updates,
    )
    caption_segment_matching.set_video_caption_match_aggregates(
        session=session,
        video_sample_id=video.sample_id,
        scores=primary_scores,
    )
    caption_segment_matching.set_video_caption_frame_score_aggregates(
        session=session,
        video_sample_id=video.sample_id,
        scores=scores,
    )
    return scores


def _print_caption_match_summary(
    score_batches: list[caption_segment_matching.CaptionSegmentFrameScores],
    primary_scoring: CaptionMatchScoring,
) -> None:
    mean_scores = [score for batch in score_batches for score in batch.mean_pooled_scores]
    top_k_scores = [score for batch in score_batches for score in batch.top_k_scores]
    margins = [
        margin
        for batch in score_batches
        for margin in batch.alignment_margins
        if margin is not None
    ]
    if not mean_scores:
        return

    summary = (
        f"Caption matching: primary={primary_scoring}, captions={len(mean_scores)}, "
        f"mean_pool_median={statistics.median(mean_scores):.3f}, "
        f"top2_median={statistics.median(top_k_scores):.3f}"
    )
    if margins:
        positive_fraction = sum(margin > 0.0 for margin in margins) / len(margins)
        summary += (
            f", hard_negative_margins={len(margins)}, "
            f"margin_median={statistics.median(margins):.3f}, "
            f"positive_margin={positive_fraction:.1%}"
        )
    print(summary)


def _detect_repeated_captions(video: VideoSample, batch: CaptionEmbeddingBatch) -> None:
    if len(batch.intervals) < MIN_CAPTIONS_FOR_REPETITION:
        return
    result = caption_repetition.find_repeated_captions(
        caption_embeddings=batch.embeddings,
        intervals=batch.intervals,
    )
    caption_repetition.write_caption_repetition_metadata(
        session=video.get_object_session(),
        caption_sample_ids=batch.caption_sample_ids,
        video_sample_id=video.sample_id,
        result=result,
        caption_embeddings=batch.embeddings,
    )


def _write_qa_summary(
    video: VideoSample,
    include_legacy_caption_threshold: bool,
) -> None:
    session = video.get_object_session()
    issues = []
    quality_checks = [
        ("blur_score", 50.0, "blurry"),
        ("lighting_score", 0.45, "poor_lighting"),
        ("motion_score", 3.0, "static_camera"),
        ("whisper_caption_count", 1.0, "no_action_phrases"),
        (
            "whisper_words_per_minute",
            MIN_NARRATION_WORDS_PER_MINUTE,
            "low_narration_density",
        ),
    ]
    if include_legacy_caption_threshold:
        quality_checks.append(
            (
                caption_segment_matching.MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
                LOW_CAPTION_MATCH_MAX,
                "low_caption_match",
            )
        )
    for key, threshold, issue in quality_checks:
        value = metadata_resolver.get_value_for_sample(
            session=session,
            sample_id=video.sample_id,
            key=key,
        )
        if isinstance(value, (int, float)) and value < threshold:
            issues.append(issue)
    metadata_resolver.bulk_update_metadata(
        session,
        [
            (
                video.sample_id,
                {
                    "automated_qa_status": "review" if issues else "pass",
                    "automated_qa_issue_count": len(issues),
                    "automated_qa_issues": ", ".join(issues),
                },
            )
        ],
    )


def _infer_expected_label(file_name: str) -> str:
    normalized = file_name.lower()
    if "accepted" in normalized:
        return "accepted"
    if "rejected" in normalized or "reject_" in normalized:
        return "rejected"
    return "unlabeled"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos", type=Path, default=DEFAULT_VIDEOS_PATH)
    parser.add_argument("--db-file", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--transcript-cache", type=Path, default=DEFAULT_TRANSCRIPT_CACHE)
    parser.add_argument("--whisper-python", type=Path, default=DEFAULT_WHISPER_PYTHON)
    parser.add_argument("--whisper-model", default="turbo")
    parser.add_argument("--whisper-device", default="auto", choices=("auto", "cuda", "cpu"))
    parser.add_argument("--whisper-compute-type", default="default")
    parser.add_argument("--whisper-beam-size", type=int, default=5)
    parser.add_argument("--disable-vad", action="store_true")
    parser.add_argument("--vad-threshold", type=float, default=0.5)
    parser.add_argument("--vad-min-silence-ms", type=int, default=500)
    parser.add_argument(
        "--caption-unit",
        choices=("segment", "word", "action_phrase"),
        default="action_phrase",
    )
    parser.add_argument("--action-pause-s", type=float, default=0.8)
    parser.add_argument("--action-window-padding-s", type=float, default=1.0)
    parser.add_argument("--action-min-window-s", type=float, default=2.5)
    parser.add_argument("--action-max-words", type=int, default=12)
    parser.add_argument(
        "--pe-model", choices=SUPPORTED_MODEL_NAMES, default=SUPPORTED_MODEL_NAMES[0]
    )
    parser.add_argument(
        "--caption-match-scoring",
        choices=("mean_pool", "top2"),
        default="mean_pool",
        help="Score shown by the existing caption-match timeline and video aggregates.",
    )
    parser.add_argument("--force-transcribe", action="store_true")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-gui", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run_pipeline(args=_parse_args())
