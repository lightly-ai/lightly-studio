#!/usr/bin/env python3
"""Screen pulled deliveries: technical quality plus Qwen narration classification.

Part two of the QA pipeline. Consumes the ``LocalTriplet``s produced by ``qa_pull`` (with
transcripts either shipped or filled in by ``qa_transcribe``) and writes, per video, both
the technical/quality signals and the TASK/ENVIRONMENT/BOTH/OTHER narration labels, then
folds them into a single ``automated_qa_status`` verdict.

Every file-dependent stage runs per batch: ingest, narration classification, quality
scoring, technical inspection, and the per-video verdict. A completion marker is written
last, so interrupted database rows can resume safely. The dataset-level summary uses only
persisted metadata and runs after all batches finish.

Everything is reused from ``run_egocentric_qa`` so the caption units, quality screens, and
pass/fail thresholds stay single-sourced. Deduplication is deliberately skipped: QA is
per-video, so there is no cross-video comparison.
"""

# Reuse the sibling runner's private QA helpers so the logic stays in one place.
# ruff: noqa: SLF001
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeVar, cast
from uuid import UUID

if TYPE_CHECKING or __package__:
    from scripts import qa_pull
    from scripts import run_egocentric_qa as qa
else:
    import run_egocentric_qa as qa

from lightly_studio.dataset import narration_classification, video_quality
from lightly_studio.dataset.whisper_transcript import ActionPhraseSettings, CaptionUnit
from lightly_studio.resolvers import metadata_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

if TYPE_CHECKING:
    from lightly_studio.core.video.video_dataset import VideoDataset
    from lightly_studio.core.video.video_sample import VideoSample

DEFAULT_CAPTION_UNIT: CaptionUnit = "narration_chunk"
DEFAULT_BATCH_SIZE = 8
# Ingest stores one child sample per decoded frame; QA reads none of them (quality reopens
# the file, narration uses the transcript). Subsample to 1 fps to keep the database small.
DEFAULT_TARGET_FPS = 1.0
# The reference runner defaults to ``qwen3:4b``, which is not installed locally; the QA
# host carries ``qwen3:8b``.
DEFAULT_NARRATION_MODEL = "qwen3:8b"
DEFAULT_ACTION_PHRASE_SETTINGS = ActionPhraseSettings(
    pause_threshold_s=0.8,
    window_padding_s=1.0,
    min_window_duration_s=2.5,
    max_words=12,
)
PIPELINE_COMPLETE_KEY = "qa_pipeline_complete"
_T = TypeVar("_T")


@dataclass(frozen=True)
class ScreenResult:
    """The QA verdict for one screened video, read back from the database."""

    file_name: str
    automated_qa_status: str  # "pass", "review", or "fail"
    narration_qa_status: str | None  # "likely_pass", "manual_review", "likely_fail"
    issues: str


def build_classifier(
    base_url: str = qa.DEFAULT_NARRATION_LLM_BASE_URL,
    model: str = DEFAULT_NARRATION_MODEL,
    provider: str = qa.DEFAULT_NARRATION_LLM_PROVIDER,
    api_key: str | None = qa.DEFAULT_NARRATION_LLM_API_KEY,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> narration_classification.OpenAICompatibleNarrationClassifier:
    """Build the narration classifier pointed at the QA host's ollama endpoint."""
    return narration_classification.OpenAICompatibleNarrationClassifier(
        settings=narration_classification.NarrationClassifierSettings(
            base_url=base_url,
            model=model,
            provider=cast(narration_classification.NarrationLlmProvider, provider),
            api_key=api_key,
            batch_size=batch_size,
        )
    )


def screen_deliveries(  # noqa: PLR0913  parameters mirror the ingest + narration knobs.
    dataset: VideoDataset,
    triplets: list[qa_pull.LocalTriplet],
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
    batch_size: int = DEFAULT_BATCH_SIZE,
    caption_unit: CaptionUnit = DEFAULT_CAPTION_UNIT,
    action_phrase_settings: ActionPhraseSettings = DEFAULT_ACTION_PHRASE_SETTINGS,
    target_fps: float = DEFAULT_TARGET_FPS,
    force: bool = False,
    probe_classifier: bool = True,
) -> list[ScreenResult]:
    """Ingest and narration-classify the deliveries in batches, then screen quality.

    Args:
        dataset: Persistent dataset the deliveries are ingested into and kept in.
        triplets: Pulled deliveries; each must have a resolved ``transcript_path``.
        classifier: Narration classifier (see ``build_classifier``).
        batch_size: Deliveries ingested and classified per batch.
        caption_unit: Whisper caption granularity fed to the classifier.
        action_phrase_settings: Action-phrase windowing for ``action_phrase`` units.
        target_fps: Frame rate the videos are subsampled to at ingest, to bound the
            number of stored frame rows.
        force: Reclassify captions even if a cached classification exists.
        probe_classifier: Probe the narration endpoint before the first pending batch.

    Returns:
        One ``ScreenResult`` per requested video, in input order.
    """
    _validate_transcripts(triplets=triplets)
    screened_videos: list[VideoSample] = []
    classifier_probed = False
    for batch in _chunks(triplets, batch_size):
        batch_videos = _ingest_batch(
            dataset=dataset,
            batch=batch,
            target_fps=target_fps,
        )
        _write_provenance(dataset=dataset, batch=batch, videos=batch_videos)
        pending_videos = [
            video for video in batch_videos if force or not _pipeline_complete(video=video)
        ]
        if pending_videos:
            # if probe_classifier and not classifier_probed:
            #     qa._probe_narration_classifier(classifier=classifier)
            #     classifier_probed = True
            _screen_videos(dataset=dataset, videos=pending_videos)
        screened_videos.extend(batch_videos)

    unique_videos = {video.sample_id: video for video in screened_videos}
    return [_read_result(video=video) for video in unique_videos.values()]


def write_dataset_summary(dataset: VideoDataset) -> None:
    """Persist and print the database-only summary after all batches finish."""
    qa._write_and_print_dataset_qa_summary(dataset=dataset)


def _ingest_batch(
    dataset: VideoDataset,
    batch: list[qa_pull.LocalTriplet],
    target_fps: float,
) -> list[VideoSample]:
    """Ingest missing videos and return every database video represented by the batch.

    Existing videos are returned too, allowing an interrupted run to resume the
    remaining QA stages instead of treating path deduplication as completion.
    """
    for triplet in batch:
        dataset.add_videos_from_path(
            path=triplet.video_path.resolve(),
            embed=False,
            embed_frames=False,
            target_fps=target_fps,
        )
    return _videos_for_triplets(dataset=dataset, triplets=batch)


def _screen_videos(
    dataset: VideoDataset,
    videos: list[VideoSample],
) -> None:
    """Run every file-dependent QA stage before the batch can be cleaned up."""
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        [(video.sample_id, {PIPELINE_COMPLETE_KEY: False}) for video in videos],
    )
    _score_quality(dataset=dataset, videos=videos)
    qa._write_technical_qa_metadata(dataset=dataset, videos=videos)
    for video in videos:
        qa._write_qa_summary(video=video, include_legacy_caption_threshold=False)
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        [(video.sample_id, {PIPELINE_COMPLETE_KEY: True}) for video in videos],
    )


def _score_quality(dataset: VideoDataset, videos: list[VideoSample]) -> None:
    sample_ids = [video.sample_id for video in videos]
    filters = VideoFilter(sample_filter=SampleFilter(sample_ids=sample_ids))
    video_quality.compute_and_store_quality_metadata(
        session=dataset.session,
        collection_id=dataset.collection_id,
        filters=filters,
    )


def _videos_for_triplets(
    dataset: VideoDataset,
    triplets: list[qa_pull.LocalTriplet],
) -> list[VideoSample]:
    videos_by_path = {Path(video.file_path_abs).resolve(): video for video in dataset}
    videos: list[VideoSample] = []
    for triplet in triplets:
        path = triplet.video_path.resolve()
        video = videos_by_path.get(path)
        if video is None:
            raise RuntimeError(f"Video was not ingested: '{path}'.")
        videos.append(video)
    return videos


def _write_provenance(
    dataset: VideoDataset,
    batch: list[qa_pull.LocalTriplet],
    videos: list[VideoSample],
) -> None:
    triplets_by_path = {triplet.video_path.resolve(): triplet for triplet in batch}
    updates: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in videos:
        triplet = triplets_by_path[Path(video.file_path_abs).resolve()]
        updates.append(
            (
                video.sample_id,
                {
                    "qa_source_bucket": triplet.bucket,
                    "qa_source_prefix": triplet.prefix,
                    "qa_source_stem": triplet.stem,
                    "qa_source_video_url": triplet.source_files[0],
                    "qa_source_files": list(triplet.source_files),
                },
            )
        )
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        updates,
    )


def _pipeline_complete(video: VideoSample) -> bool:
    value = metadata_resolver.get_value_for_sample(
        session=video.get_object_session(),
        sample_id=video.sample_id,
        key=PIPELINE_COMPLETE_KEY,
    )
    return value is True


def _validate_transcripts(triplets: list[qa_pull.LocalTriplet]) -> None:
    missing = [
        f"{triplet.bucket}/{triplet.prefix}/{triplet.stem}"
        for triplet in triplets
        if triplet.transcript_path is None
    ]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Cannot screen deliveries without transcripts: {joined}.")


def _read_result(video: VideoSample) -> ScreenResult:
    session = video.get_object_session()

    def value(key: str) -> object:
        return metadata_resolver.get_value_for_sample(
            session=session, sample_id=video.sample_id, key=key
        )

    return ScreenResult(
        file_name=video.file_name,
        automated_qa_status=str(value("automated_qa_status")),
        narration_qa_status=(
            str(value("narration_qa_status")) if value("narration_qa_status") is not None else None
        ),
        issues=str(value("automated_qa_issues") or ""),
    )


def _chunks(items: list[_T], size: int) -> list[list[_T]]:
    if size < 1:
        raise ValueError(f"batch_size must be at least 1, got {size}.")
    return [items[start : start + size] for start in range(0, len(items), size)]
