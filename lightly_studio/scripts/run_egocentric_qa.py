"""Transcribe egocentric videos, compute QA signals, and launch LightlyStudio."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import statistics
import subprocess
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from tqdm import tqdm

import lightly_studio as ls
from lightly_studio.core.video.add_videos import VIDEO_EXTENSIONS
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import (
    caption_embedding,
    caption_repetition,
    caption_segment_matching,
    egocentric_qa,
    narration_classification,
    video_quality,
    whisper_transcript,
)
from lightly_studio.dataset.embedding_manager import EmbeddingManagerProvider
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    SUPPORTED_MODEL_NAMES,
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.dataset.whisper_transcript import ActionPhraseSettings, CaptionUnit
from lightly_studio.models.caption import CaptionCreate, CaptionTable
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
DEFAULT_NARRATION_LLM_BASE_URL = os.environ.get("NARRATION_LLM_BASE_URL", "http://localhost:11434")
DEFAULT_NARRATION_LLM_MODEL = os.environ.get("NARRATION_LLM_MODEL", "qwen3:4b")
DEFAULT_NARRATION_LLM_API_KEY = os.environ.get("NARRATION_LLM_API_KEY")
DEFAULT_NARRATION_LLM_PROVIDER = os.environ.get("NARRATION_LLM_PROVIDER", "ollama")
WHISPER_WORKER_PATH = PROJECT_ROOT / "scripts" / "transcribe_with_faster_whisper.py"
LOW_CAPTION_MATCH_MAX = caption_segment_matching.DEFAULT_MIN_CAPTION_SEGMENT_MATCH_SCORE
MIN_CAPTIONS_FOR_REPETITION = 2
MIN_NARRATION_WORDS_PER_MINUTE = egocentric_qa.MIN_NARRATION_WORDS_PER_MINUTE
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
    classifier = _create_narration_classifier(args=args) if args.narration else None
    if classifier is not None:
        _probe_narration_classifier(classifier=classifier)
    else:
        print("Skipping narration classification (enable with --narration).", flush=True)
    transcript_paths = _ensure_transcripts(video_paths=video_paths, args=args)

    db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=True)
    dataset = VideoDataset.create(name="egocentric-qa")
    dataset.add_videos_from_path(path=videos_path, embed=False, embed_frames=False)
    dataset.compute_quality_scores()
    _write_technical_qa_metadata(dataset=dataset)

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
    if classifier is not None:
        _classify_narration_captions(
            dataset=dataset,
            captions_by_video=captions_by_video,
            classifier=classifier,
            force=args.force_classify,
        )

    frame_score_batches = []
    if args.enable_pe_diagnostics:
        embedding_generator = PerceptionEncoderEmbeddingGenerator(model_name=args.pe_model)
        ls.set_default_embedding_model(embedding_generator)
        all_caption_ids = [
            caption_id for _, caption_ids in captions_by_video for caption_id in caption_ids
        ]
        caption_embedding.embed_captions(
            session=dataset.session,
            caption_sample_ids=all_caption_ids,
        )
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

    for video, _ in captions_by_video:
        _write_qa_summary(
            video=video,
            include_legacy_caption_threshold=(
                args.enable_pe_diagnostics and args.caption_match_scoring == "mean_pool"
            ),
            include_narration_checks=args.narration,
        )

    _write_and_print_dataset_qa_summary(dataset=dataset)
    if args.enable_pe_diagnostics:
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
    video_paths = sorted(
        path.resolve()
        for path in videos_path.rglob("*")
        if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not video_paths:
        raise FileNotFoundError(f"No supported videos found under: '{videos_path}'.")
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
    videos: Iterable[VideoSample] | None = None,
) -> list[tuple[VideoSample, list[UUID]]]:
    captions_by_video: list[tuple[VideoSample, list[UUID]]] = []
    video_metadata: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in dataset if videos is None else videos:
        transcript_path = transcript_paths[Path(video.file_path_abs).resolve()]
        video_duration_s = float(video.duration_s) if video.duration_s is not None else None
        transcript = whisper_transcript.load_whisper_transcript(
            transcript_path,
            caption_unit=caption_unit,
            video_duration_s=video_duration_s,
            action_phrase_settings=action_phrase_settings,
        )
        timestamp_transcript = (
            transcript
            if caption_unit == "segment"
            else whisper_transcript.load_whisper_transcript(
                transcript_path,
                caption_unit="segment",
                video_duration_s=video_duration_s,
            )
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
                    "qa_has_narration": transcript.word_count > 0,
                    "qa_transcript_timestamps_valid": (
                        egocentric_qa.has_valid_caption_timestamps(
                            captions=timestamp_transcript.captions,
                            duration_s=video_duration_s,
                        )
                    ),
                    "qa_is_english": egocentric_qa.is_english(language=transcript.language),
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


def _create_narration_classifier(
    args: argparse.Namespace,
) -> narration_classification.OpenAICompatibleNarrationClassifier:
    return narration_classification.OpenAICompatibleNarrationClassifier(
        settings=narration_classification.NarrationClassifierSettings(
            base_url=args.narration_llm_base_url,
            model=args.narration_llm_model,
            provider=args.narration_llm_provider,
            api_key=args.narration_llm_api_key,
            batch_size=args.classification_batch_size,
        )
    )


def _probe_narration_classifier(
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
) -> None:
    print(
        f"Checking narration classifier model {classifier.model}...",
        flush=True,
    )
    classifier.probe()


def _classify_narration_captions(
    dataset: VideoDataset,
    captions_by_video: list[tuple[VideoSample, list[UUID]]],
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
    force: bool,
) -> None:
    total_chunks = sum(len(caption_ids) for _, caption_ids in captions_by_video)
    with tqdm(
        total=total_chunks,
        desc="Classifying narration",
        unit="chunk",
        dynamic_ncols=True,
    ) as progress:

        def update_progress(completed_chunk_count: int) -> None:
            progress.update(completed_chunk_count)

        for video_index, (video, caption_ids) in enumerate(captions_by_video, start=1):
            try:
                summary = _classify_video_narration(
                    dataset=dataset,
                    video=video,
                    caption_ids=caption_ids,
                    classifier=classifier,
                    force=force,
                    on_progress=update_progress,
                )
                progress.set_postfix(
                    video=f"{video_index}/{len(captions_by_video)}",
                    qualifying=f"{summary.qualifying_percentage:.1f}%",
                    status=summary.status,
                    refresh=False,
                )
            except Exception as error:  # Continue so one bad transcript does not lose the dataset.
                metadata_resolver.bulk_update_metadata(
                    dataset.session,
                    [
                        (
                            video.sample_id,
                            {
                                "narration_classification_complete": False,
                                "narration_classification_stale": True,
                                "narration_qa_status": "incomplete",
                                "narration_classification_error": str(error),
                                "narration_model": classifier.model,
                                "narration_prompt_version": narration_classification.PROMPT_VERSION,
                            },
                        )
                    ],
                )
                progress.write(f"Classification incomplete for {video.file_name}: {error}")


def _classify_video_narration(  # noqa: PLR0913
    dataset: VideoDataset,
    video: VideoSample,
    caption_ids: list[UUID],
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
    force: bool,
    on_progress: Callable[[int], None] | None = None,
) -> narration_classification.NarrationSummary:
    caption_unit = metadata_resolver.get_value_for_sample(
        session=dataset.session,
        sample_id=video.sample_id,
        key="whisper_caption_unit",
    )
    if caption_unit != "narration_chunk":
        raise ValueError(
            "Narration classification requires captions created with "
            "--caption-unit narration_chunk."
        )
    captions_by_id = {
        caption.sample_id: caption
        for caption in caption_resolver.get_by_ids(
            session=dataset.session,
            sample_ids=caption_ids,
        )
    }
    captions = [captions_by_id[caption_id] for caption_id in caption_ids]
    if not captions:
        raise ValueError("Transcript contains no narration chunks.")
    chunks = _to_narration_chunks(captions=captions)
    classifications = _load_or_classify_chunks(
        dataset=dataset,
        chunks=chunks,
        classifier=classifier,
        force=force,
        on_progress=on_progress,
    )
    classification_by_id = {
        classification.chunk_id: classification for classification in classifications
    }
    caption_metadata = [
        (
            UUID(chunk.id),
            narration_classification.classification_metadata(
                classification=classification_by_id[chunk.id],
                text=chunk.text,
                model=classifier.model,
            ),
        )
        for chunk in chunks
    ]
    summary = narration_classification.summarize_classifications(
        chunks=chunks,
        classifications=classifications,
    )
    video_metadata = narration_classification.summary_metadata(
        summary=summary,
        model=classifier.model,
    )
    video_metadata["narration_classification_error"] = ""
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        [*caption_metadata, (video.sample_id, video_metadata)],
    )
    return summary


def _to_narration_chunks(
    captions: Sequence[CaptionTable],
) -> list[narration_classification.NarrationChunk]:
    return [
        narration_classification.NarrationChunk(
            id=str(caption.sample_id),
            text=caption.text,
            previous_text=captions[index - 1].text if index > 0 else None,
            next_text=captions[index + 1].text if index + 1 < len(captions) else None,
        )
        for index, caption in enumerate(captions)
    ]


def _load_or_classify_chunks(
    dataset: VideoDataset,
    chunks: list[narration_classification.NarrationChunk],
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
    force: bool,
    on_progress: Callable[[int], None] | None = None,
) -> list[narration_classification.NarrationClassification]:
    classifications: dict[str, narration_classification.NarrationClassification] = {}
    if not force:
        for chunk in chunks:
            metadata_row = metadata_resolver.get_by_sample_id(
                session=dataset.session,
                sample_id=UUID(chunk.id),
            )
            metadata = metadata_row.data if metadata_row is not None else None
            cached = narration_classification.classification_from_metadata(
                metadata=metadata,
                chunk_id=chunk.id,
                text=chunk.text,
                model=classifier.model,
            )
            if cached is not None:
                classifications[chunk.id] = cached
    if on_progress is not None:
        on_progress(len(classifications))
    missing_chunks = [chunk for chunk in chunks if chunk.id not in classifications]
    chunk_by_id = {chunk.id: chunk for chunk in chunks}

    def checkpoint_batch(
        batch: Sequence[narration_classification.NarrationClassification],
    ) -> None:
        metadata_resolver.bulk_update_metadata(
            dataset.session,
            [
                (
                    UUID(classification.chunk_id),
                    narration_classification.classification_metadata(
                        classification=classification,
                        text=chunk_by_id[classification.chunk_id].text,
                        model=classifier.model,
                    ),
                )
                for classification in batch
            ],
        )
        classifications.update(
            {classification.chunk_id: classification for classification in batch}
        )
        if on_progress is not None:
            on_progress(len(batch))

    classifier.classify(
        chunks=missing_chunks,
        on_batch_complete=checkpoint_batch,
    )
    return [classifications[chunk.id] for chunk in chunks]


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


def _write_technical_qa_metadata(
    dataset: VideoDataset,
    videos: Iterable[VideoSample] | None = None,
) -> None:
    metadata_updates: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in dataset if videos is None else videos:
        duration_s = float(video.duration_s) if video.duration_s is not None else None
        video_path = video.file_path_abs
        metadata_updates.append(
            (
                video.sample_id,
                {
                    "qa_resolution_pass": egocentric_qa.has_minimum_1080p_resolution(
                        width=video.width,
                        height=video.height,
                    ),
                    "qa_duration_pass": egocentric_qa.has_valid_duration(duration_s=duration_s),
                    "qa_has_audio": egocentric_qa.has_audio_stream(video_path=video_path),
                    "qa_orientation": egocentric_qa.get_orientation(
                        width=video.width,
                        height=video.height,
                    ),
                    "qa_media_format": Path(video_path).suffix.lower().lstrip("."),
                    "qa_preferred_format": egocentric_qa.has_preferred_video_format(
                        video_path=video_path
                    ),
                },
            )
        )
    metadata_resolver.bulk_update_metadata(dataset.session, metadata_updates)


def _write_qa_summary(
    video: VideoSample,
    include_legacy_caption_threshold: bool,
    include_narration_checks: bool = True,
) -> None:
    session = video.get_object_session()
    failures = []
    review_issues = []
    required_checks = [
        ("qa_resolution_pass", "low_resolution"),
        ("qa_duration_pass", "invalid_duration"),
        ("qa_has_audio", "no_audio_stream"),
        ("qa_has_narration", "no_narration"),
        ("whisper_wpm_pass", "low_narration_density"),
        ("qa_transcript_timestamps_valid", "invalid_transcript_timestamps"),
    ]
    if include_narration_checks:
        required_checks.extend(
            [
                ("narration_classification_complete", "narration_classification_incomplete"),
                ("narration_requirement_pass", "insufficient_task_environment_narration"),
            ]
        )
    review_checks = [
        (
            video_quality.BLUR_SCORE_KEY,
            video_quality.DEFAULT_BLUR_SCORE_LOW_MAX,
            "blurry",
        ),
        (
            video_quality.LIGHTING_SCORE_KEY,
            video_quality.DEFAULT_LIGHTING_SCORE_LOW_MAX,
            "poor_lighting",
        ),
        (
            video_quality.MOTION_SCORE_KEY,
            video_quality.DEFAULT_MOTION_SCORE_LOW_MAX,
            "static_camera",
        ),
        (
            "whisper_caption_count",
            float(egocentric_qa.MIN_NARRATION_CAPTION_COUNT),
            "no_action_phrases",
        ),
    ]
    if include_legacy_caption_threshold:
        review_checks.append(
            (
                caption_segment_matching.MIN_CAPTION_SEGMENT_MATCH_SCORE_KEY,
                LOW_CAPTION_MATCH_MAX,
                "low_caption_match",
            )
        )
    for key, issue in required_checks:
        value = metadata_resolver.get_value_for_sample(
            session=session,
            sample_id=video.sample_id,
            key=key,
        )
        if value is not True:
            failures.append(issue)
    for key, threshold, issue in review_checks:
        value = metadata_resolver.get_value_for_sample(
            session=session,
            sample_id=video.sample_id,
            key=key,
        )
        if isinstance(value, (int, float)) and value < threshold:
            review_issues.append(issue)
    repeated_group_count = metadata_resolver.get_value_for_sample(
        session=session,
        sample_id=video.sample_id,
        key=caption_repetition.REPEATED_CAPTION_GROUP_COUNT_KEY,
    )
    if isinstance(repeated_group_count, (int, float)) and repeated_group_count > 0:
        review_issues.append("repeated_actions")
    if failures:
        status = "fail"
    elif review_issues:
        status = "review"
    else:
        status = "pass"
    issues = [*failures, *review_issues]
    metadata_resolver.bulk_update_metadata(
        session,
        [
            (
                video.sample_id,
                {
                    "qa_deterministic_pass": not failures,
                    "automated_qa_status": status,
                    "automated_qa_failure_count": len(failures),
                    "automated_qa_failures": ", ".join(failures),
                    "automated_qa_review_issue_count": len(review_issues),
                    "automated_qa_review_issues": ", ".join(review_issues),
                    "automated_qa_issue_count": len(issues),
                    "automated_qa_issues": ", ".join(issues),
                },
            )
        ],
    )


def _write_and_print_dataset_qa_summary(dataset: VideoDataset) -> None:
    videos = list(dataset)
    records = []
    statuses = {"pass": 0, "review": 0, "fail": 0}
    for video in videos:
        metadata_row = metadata_resolver.get_by_sample_id(
            session=dataset.session,
            sample_id=video.sample_id,
        )
        metadata = metadata_row.data if metadata_row is not None else {}
        motion_score = metadata.get(video_quality.MOTION_SCORE_KEY)
        records.append(
            egocentric_qa.DatasetVideoQa(
                duration_s=(float(video.duration_s) if video.duration_s is not None else None),
                language=_as_optional_string(metadata.get("whisper_language")),
                is_static_camera=(
                    isinstance(motion_score, (int, float))
                    and motion_score < video_quality.DEFAULT_MOTION_SCORE_LOW_MAX
                ),
            )
        )
        status = metadata.get("automated_qa_status")
        if isinstance(status, str) and status in statuses:
            statuses[status] += 1

    summary = egocentric_qa.summarize_dataset(records=records)
    summary_metadata = {
        "qa_dataset_average_duration_minutes": (
            summary.average_duration_s / 60.0 if summary.average_duration_s is not None else None
        ),
        "qa_dataset_average_duration_pass": summary.average_duration_pass,
        "qa_dataset_english_video_percentage": summary.english_video_ratio * 100.0,
        "qa_dataset_english_ratio_pass": summary.english_video_ratio_pass,
        "qa_dataset_static_camera_percentage": summary.static_camera_ratio * 100.0,
        "qa_dataset_static_camera_minority_pass": summary.static_camera_minority_pass,
    }
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        [(video.sample_id, summary_metadata) for video in videos],
    )
    _print_dataset_qa_summary(summary=summary, statuses=statuses)


def _print_dataset_qa_summary(
    summary: egocentric_qa.DatasetQaSummary,
    statuses: Mapping[str, int],
) -> None:
    average_minutes = (
        f"{summary.average_duration_s / 60.0:.2f} min"
        if summary.average_duration_s is not None
        else "unknown"
    )
    print("Dataset requirements:")
    print(
        f"  Average duration: {average_minutes} "
        f"({_pass_label(summary.average_duration_pass)}; required 1-5 min)"
    )
    print(
        f"  English videos: {summary.english_video_count}/{summary.video_count} "
        f"({summary.english_video_ratio:.1%}, "
        f"{_pass_label(summary.english_video_ratio_pass)}; required >=50%)"
    )
    print(
        f"  Static-camera videos: {summary.static_camera_count}/{summary.video_count} "
        f"({summary.static_camera_ratio:.1%}, "
        f"{_pass_label(summary.static_camera_minority_pass)}; required <50%)"
    )
    print(
        "  Per-video automated status: "
        f"pass={statuses['pass']}, review={statuses['review']}, fail={statuses['fail']}"
    )


def _as_optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _pass_label(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


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
        choices=("segment", "word", "action_phrase", "narration_chunk"),
        default="narration_chunk",
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
    parser.add_argument("--force-classify", action="store_true")
    parser.add_argument(
        "--narration",
        action="store_true",
        help="Run the Qwen narration classification and its task/environment pass check "
        "(off by default).",
    )
    parser.add_argument(
        "--narration-llm-base-url",
        default=DEFAULT_NARRATION_LLM_BASE_URL,
    )
    parser.add_argument(
        "--narration-llm-provider",
        choices=("ollama", "openai"),
        default=DEFAULT_NARRATION_LLM_PROVIDER,
    )
    parser.add_argument("--narration-llm-model", default=DEFAULT_NARRATION_LLM_MODEL)
    parser.add_argument("--narration-llm-api-key", default=DEFAULT_NARRATION_LLM_API_KEY)
    parser.add_argument(
        "--classification-batch-size",
        type=int,
        default=narration_classification.DEFAULT_BATCH_SIZE,
    )
    parser.add_argument(
        "--enable-pe-diagnostics",
        action="store_true",
        help="Run the slower PE caption matching and repetition diagnostics.",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-gui", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run_pipeline(args=_parse_args())
