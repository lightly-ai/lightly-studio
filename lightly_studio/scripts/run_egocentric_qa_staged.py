"""Run the egocentric QA workflow one observable stage at a time.

This diagnostic entry point follows the linear structure of the timed-caption examples.
Use ``--stop-after`` to prove that each stage completes before including the next one.
Long-running stages print their start, completion, and elapsed time.
"""

# This diagnostic runner intentionally reuses the existing script's private stages so
# behavior stays comparable while the freeze is isolated.
# ruff: noqa: SLF001

from __future__ import annotations

import argparse
import contextlib
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import run_egocentric_qa as pipeline
import sqlmodel

import lightly_studio as ls
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.database import db_manager
from lightly_studio.dataset import (
    caption_embedding,
    caption_segment_matching,
    narration_classification,
)
from lightly_studio.dataset.perception_encoder_embedding_generator import (
    SUPPORTED_MODEL_NAMES,
    PerceptionEncoderEmbeddingGenerator,
)
from lightly_studio.dataset.whisper_transcript import ActionPhraseSettings
from lightly_studio.models.caption import CaptionTable

DEFAULT_DATABASE_PATH = pipeline.PROJECT_ROOT / "egocentric_qa_staged.db"
STAGES = (
    "discover",
    "classifier-check",
    "transcribe",
    "database",
    "videos",
    "quality",
    "model",
    "captions",
    "narration-classification",
    "caption-embeddings",
    "caption-matching",
    "repetition",
    "qa-summary",
    "gui",
)


def run_staged_pipeline(  # noqa: C901, PLR0911, PLR0912, PLR0915
    args: argparse.Namespace,
) -> None:
    """Run the pipeline with observable boundaries and optional early stopping.

    Args:
        args: Parsed command-line arguments.
    """
    if args.only_stage is not None:
        _run_only_stage(args=args, stage=args.only_stage)
        return

    with _stage("discover"):
        video_paths = _discover_videos(args=args)
    if _stop_after(args=args, stage="discover"):
        return

    with _stage("classifier-check"):
        classifier = pipeline._create_narration_classifier(args=args)
        pipeline._probe_narration_classifier(classifier=classifier)
    if _stop_after(args=args, stage="classifier-check"):
        return

    with _stage("transcribe"):
        transcript_paths = pipeline._ensure_transcripts(video_paths=video_paths, args=args)
    if _stop_after(args=args, stage="transcribe"):
        return

    with _stage("database"):
        print(f"Recreating diagnostic database at {args.db_file.resolve()}...", flush=True)
        db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=True)
        dataset = VideoDataset.create(name="egocentric-qa-staged")
    if _stop_after(args=args, stage="database"):
        return

    with _stage("videos"):
        _add_videos(dataset=dataset, video_paths=video_paths)
    if _stop_after(args=args, stage="videos"):
        return

    with _stage("quality"):
        dataset.compute_quality_scores()
        pipeline._write_technical_qa_metadata(dataset=dataset)
    if _stop_after(args=args, stage="quality"):
        return

    with _stage("model"):
        embedding_generator = None
        if args.enable_pe_diagnostics:
            print(f"Loading Perception Encoder model {args.pe_model}...", flush=True)
            embedding_generator = PerceptionEncoderEmbeddingGenerator(model_name=args.pe_model)
            ls.set_default_embedding_model(embedding_generator)
        else:
            print("PE diagnostics disabled; skipping model load.", flush=True)
    if _stop_after(args=args, stage="model"):
        return

    with _stage("captions"):
        captions_by_video = pipeline._create_transcript_captions(
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
        caption_count = sum(len(caption_ids) for _, caption_ids in captions_by_video)
        print(f"Created {caption_count} caption(s).", flush=True)
    if _stop_after(args=args, stage="captions"):
        return

    with _stage("narration-classification"):
        pipeline._classify_narration_captions(
            dataset=dataset,
            captions_by_video=captions_by_video,
            classifier=classifier,
            force=args.force_classify,
        )
    if _stop_after(args=args, stage="narration-classification"):
        return

    with _stage("caption-embeddings"):
        if args.enable_pe_diagnostics:
            all_caption_ids = [
                caption_id for _, caption_ids in captions_by_video for caption_id in caption_ids
            ]
            caption_embedding.embed_captions(
                session=dataset.session,
                caption_sample_ids=all_caption_ids,
            )
        else:
            print("PE diagnostics disabled; skipping caption embeddings.", flush=True)
    if _stop_after(args=args, stage="caption-embeddings"):
        return

    with _stage("caption-matching"):
        batches: list[tuple[VideoSample, pipeline.CaptionEmbeddingBatch]] = []
        if args.enable_pe_diagnostics:
            if embedding_generator is None:
                raise RuntimeError("PE embedding generator was not loaded.")
            batches, frame_score_batches = _score_captions(
                captions_by_video=captions_by_video,
                embedding_generator=embedding_generator,
                primary_scoring=args.caption_match_scoring,
            )
            pipeline._print_caption_match_summary(
                score_batches=frame_score_batches,
                primary_scoring=args.caption_match_scoring,
            )
        else:
            print("PE diagnostics disabled; skipping caption matching.", flush=True)
    if _stop_after(args=args, stage="caption-matching"):
        return

    with _stage("repetition"):
        if args.enable_pe_diagnostics:
            for video, batch in batches:
                print(f"Checking repetitions in {video.file_name}...", flush=True)
                pipeline._detect_repeated_captions(video=video, batch=batch)
        else:
            print("PE diagnostics disabled; skipping repetition detection.", flush=True)
    if _stop_after(args=args, stage="repetition"):
        return

    with _stage("qa-summary"):
        for video, _ in captions_by_video:
            pipeline._write_qa_summary(
                video=video,
                include_legacy_caption_threshold=(
                    args.enable_pe_diagnostics and args.caption_match_scoring == "mean_pool"
                ),
            )
        pipeline._write_and_print_dataset_qa_summary(dataset=dataset)
        print(f"Indexed {len(video_paths)} video(s) in {args.db_file.resolve()}.", flush=True)
    if args.no_gui or _stop_after(args=args, stage="qa-summary"):
        return

    with _stage("gui"):
        print(
            "The GUI runs in the foreground and is expected to stay here until you press Ctrl-C.",
            flush=True,
        )
        ls.start_gui(host=args.host, port=args.port)


def _run_only_stage(  # noqa: C901, PLR0911, PLR0912, PLR0915
    args: argparse.Namespace,
    stage: str,
) -> None:
    """Run exactly one stage, loading existing state when required."""
    if stage == "discover":
        with _stage(stage):
            _discover_videos(args=args)
        return

    if stage == "classifier-check":
        with _stage(stage):
            classifier = pipeline._create_narration_classifier(args=args)
            pipeline._probe_narration_classifier(classifier=classifier)
        return

    if stage == "transcribe":
        with _stage(stage):
            video_paths = _find_selected_videos(args=args)
            pipeline._ensure_transcripts(video_paths=video_paths, args=args)
        return

    if stage == "database":
        with _stage(stage):
            print(f"Recreating diagnostic database at {args.db_file.resolve()}...", flush=True)
            db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=True)
            VideoDataset.create(name="egocentric-qa-staged")
        return

    dataset = _load_existing_dataset(args=args)
    if stage == "videos":
        with _stage(stage):
            _add_videos(dataset=dataset, video_paths=_find_selected_videos(args=args))
        return
    if stage == "quality":
        with _stage(stage):
            dataset.compute_quality_scores()
            pipeline._write_technical_qa_metadata(dataset=dataset)
        return

    if stage == "model":
        with _stage(stage):
            _load_embedding_generator(model_name=args.pe_model)
        return

    captions_by_video = _get_existing_captions_by_video(
        dataset=dataset,
        limit=args.max_videos,
    )
    if stage == "captions":
        if any(caption_ids for _, caption_ids in captions_by_video):
            raise RuntimeError(
                "The staged database already contains captions. Continue with "
                "'--only-stage narration-classification' instead of creating duplicates."
            )
        with _stage(stage):
            video_paths = _find_selected_videos(args=args)
            transcript_paths = pipeline._ensure_transcripts(video_paths=video_paths, args=args)
            captions_by_video = pipeline._create_transcript_captions(
                dataset=dataset,
                transcript_paths=transcript_paths,
                caption_unit=args.caption_unit,
                action_phrase_settings=_get_action_phrase_settings(args=args),
            )
            caption_count = sum(len(caption_ids) for _, caption_ids in captions_by_video)
            print(f"Created {caption_count} caption(s).", flush=True)
        return

    if not any(caption_ids for _, caption_ids in captions_by_video):
        raise RuntimeError("No captions found. Run '--only-stage captions' first.")

    if stage == "narration-classification":
        with _stage(stage):
            classifier = pipeline._create_narration_classifier(args=args)
            pipeline._classify_narration_captions(
                dataset=dataset,
                captions_by_video=captions_by_video,
                classifier=classifier,
                force=args.force_classify,
            )
        return

    if stage == "caption-embeddings":
        with _stage(stage):
            _load_embedding_generator(model_name=args.pe_model)
            caption_embedding.embed_captions(
                session=dataset.session,
                caption_sample_ids=_flatten_caption_ids(captions_by_video=captions_by_video),
            )
        return

    if stage == "caption-matching":
        with _stage(stage):
            embedding_generator = _load_embedding_generator(model_name=args.pe_model)
            _, score_batches = _score_captions(
                captions_by_video=captions_by_video,
                embedding_generator=embedding_generator,
                primary_scoring=args.caption_match_scoring,
            )
            pipeline._print_caption_match_summary(
                score_batches=score_batches,
                primary_scoring=args.caption_match_scoring,
            )
        return

    if stage == "repetition":
        with _stage(stage):
            for video, caption_ids in captions_by_video:
                print(f"Checking repetitions in {video.file_name}...", flush=True)
                batch = pipeline._get_caption_embedding_batch(
                    video=video,
                    caption_ids=caption_ids,
                )
                pipeline._detect_repeated_captions(video=video, batch=batch)
        return

    if stage == "qa-summary":
        with _stage(stage):
            for video, _ in captions_by_video:
                pipeline._write_qa_summary(
                    video=video,
                    include_legacy_caption_threshold=(
                        args.enable_pe_diagnostics and args.caption_match_scoring == "mean_pool"
                    ),
                )
            pipeline._write_and_print_dataset_qa_summary(dataset=dataset)
        return

    with _stage("gui"):
        print(
            "The GUI runs in the foreground and is expected to stay here until you press Ctrl-C.",
            flush=True,
        )
        ls.start_gui(host=args.host, port=args.port)


def _discover_videos(args: argparse.Namespace) -> list[Path]:
    video_paths = _find_selected_videos(args=args)
    print(f"Found {len(video_paths)} video(s):", flush=True)
    for video_path in video_paths:
        print(f"  - {video_path}", flush=True)
    return video_paths


def _find_selected_videos(args: argparse.Namespace) -> list[Path]:
    video_paths = pipeline._find_videos(videos_path=args.videos.resolve())
    return _limit_video_paths(video_paths=video_paths, limit=args.max_videos)


def _load_existing_dataset(args: argparse.Namespace) -> VideoDataset:
    database_path = args.db_file.resolve()
    print(f"Loading diagnostic database at {database_path}...", flush=True)
    db_manager.connect(db_file=database_path, must_exist=True)
    return VideoDataset.load(name="egocentric-qa-staged")


def _load_embedding_generator(model_name: str) -> PerceptionEncoderEmbeddingGenerator:
    print(f"Loading Perception Encoder model {model_name}...", flush=True)
    embedding_generator = PerceptionEncoderEmbeddingGenerator(model_name=model_name)
    ls.set_default_embedding_model(embedding_generator)
    return embedding_generator


def _get_existing_captions_by_video(
    dataset: VideoDataset,
    limit: int | None = None,
) -> list[tuple[VideoSample, list[UUID]]]:
    captions_by_video = []
    videos = list(dataset)
    if limit is not None:
        videos = videos[:limit]
    for video in videos:
        statement = (
            sqlmodel.select(CaptionTable)
            .where(sqlmodel.col(CaptionTable.parent_sample_id) == video.sample_id)
            .order_by(sqlmodel.col(CaptionTable.created_at))
        )
        captions = dataset.session.exec(statement).all()
        captions_by_video.append((video, [caption.sample_id for caption in captions]))
    return captions_by_video


def _flatten_caption_ids(
    captions_by_video: list[tuple[VideoSample, list[UUID]]],
) -> list[UUID]:
    return [caption_id for _, caption_ids in captions_by_video for caption_id in caption_ids]


def _get_action_phrase_settings(args: argparse.Namespace) -> ActionPhraseSettings:
    return ActionPhraseSettings(
        pause_threshold_s=args.action_pause_s,
        window_padding_s=args.action_window_padding_s,
        min_window_duration_s=args.action_min_window_s,
        max_words=args.action_max_words,
    )


def _limit_video_paths(video_paths: list[Path], limit: int | None) -> list[Path]:
    if limit is None:
        return video_paths
    if limit < 1:
        raise ValueError(f"max-videos must be at least 1, got {limit}.")
    return video_paths[:limit]


def _add_videos(dataset: VideoDataset, video_paths: list[Path]) -> None:
    for index, video_path in enumerate(video_paths, start=1):
        print(f"Adding video {index}/{len(video_paths)}: {video_path.name}", flush=True)
        dataset.add_videos_from_path(path=video_path, embed=False, embed_frames=False)


def _score_captions(
    captions_by_video: list[tuple[VideoSample, list[UUID]]],
    embedding_generator: PerceptionEncoderEmbeddingGenerator,
    primary_scoring: pipeline.CaptionMatchScoring,
) -> tuple[
    list[tuple[VideoSample, pipeline.CaptionEmbeddingBatch]],
    list[caption_segment_matching.CaptionSegmentFrameScores],
]:
    batches = []
    frame_score_batches = []
    for video, caption_ids in captions_by_video:
        print(f"Scoring captions for {video.file_name}...", flush=True)
        batch = pipeline._get_caption_embedding_batch(video=video, caption_ids=caption_ids)
        batches.append((video, batch))
        scores = pipeline._score_caption_matches(
            video=video,
            batch=batch,
            embedding_generator=embedding_generator,
            primary_scoring=primary_scoring,
        )
        if scores is not None:
            frame_score_batches.append(scores)
    return batches, frame_score_batches


@contextlib.contextmanager
def _stage(name: str) -> Iterator[None]:
    stage_number = STAGES.index(name) + 1
    print(f"\n[{stage_number}/{len(STAGES)}] START {name}", flush=True)
    start_time = time.perf_counter()
    try:
        yield
    except BaseException:
        elapsed_s = time.perf_counter() - start_time
        print(f"[{stage_number}/{len(STAGES)}] FAILED {name} after {elapsed_s:.2f}s", flush=True)
        raise
    elapsed_s = time.perf_counter() - start_time
    print(f"[{stage_number}/{len(STAGES)}] DONE {name} in {elapsed_s:.2f}s", flush=True)


def _stop_after(args: argparse.Namespace, stage: str) -> bool:
    if args.stop_after != stage:
        return False
    print(f"Stopped after '{stage}' as requested.", flush=True)
    next_stage = STAGES[STAGES.index(stage) + 1]
    print(f"Next stage: {next_stage}", flush=True)
    return True


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--videos", type=Path, default=pipeline.DEFAULT_VIDEOS_PATH)
    parser.add_argument("--db-file", type=Path, default=DEFAULT_DATABASE_PATH)
    parser.add_argument("--transcript-cache", type=Path, default=pipeline.DEFAULT_TRANSCRIPT_CACHE)
    parser.add_argument("--whisper-python", type=Path, default=pipeline.DEFAULT_WHISPER_PYTHON)
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
        "--pe-model",
        choices=SUPPORTED_MODEL_NAMES,
        default=SUPPORTED_MODEL_NAMES[0],
    )
    parser.add_argument(
        "--caption-match-scoring",
        choices=("mean_pool", "top2"),
        default="mean_pool",
    )
    parser.add_argument("--force-transcribe", action="store_true")
    parser.add_argument("--force-classify", action="store_true")
    parser.add_argument(
        "--narration-llm-base-url",
        default=pipeline.DEFAULT_NARRATION_LLM_BASE_URL,
    )
    parser.add_argument(
        "--narration-llm-provider",
        choices=("ollama", "openai"),
        default=pipeline.DEFAULT_NARRATION_LLM_PROVIDER,
    )
    parser.add_argument(
        "--narration-llm-model",
        default=pipeline.DEFAULT_NARRATION_LLM_MODEL,
    )
    parser.add_argument(
        "--narration-llm-api-key",
        default=pipeline.DEFAULT_NARRATION_LLM_API_KEY,
    )
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
    parser.add_argument("--max-videos", type=int, help="Only process the first N videos.")
    parser.add_argument(
        "--stop-after",
        choices=STAGES[:-1],
        help="Exit after this stage completes. Rerun with the next stage to narrow a freeze.",
    )
    parser.add_argument(
        "--only-stage",
        choices=STAGES,
        help="Run only this stage, reusing the existing diagnostic database.",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--no-gui", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    run_staged_pipeline(args=_parse_args())
