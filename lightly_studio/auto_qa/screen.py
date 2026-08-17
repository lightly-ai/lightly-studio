"""Deterministic video and transcript QA checks."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from auto_qa.storage import LocalDelivery
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.core.video.video_sample import VideoSample
from lightly_studio.dataset import egocentric_qa, video_quality, whisper_transcript
from lightly_studio.models.caption import CaptionCreate
from lightly_studio.resolvers import caption_resolver, metadata_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from lightly_studio.resolvers.video_resolver.video_filter import VideoFilter

COMPLETE_KEY = "qa_pipeline_complete"
_REQUIRED_CHECKS = {
    "qa_resolution_pass": "low_resolution",
    "qa_duration_pass": "invalid_duration",
    "qa_has_audio": "no_audio_stream",
    "qa_has_narration": "no_narration",
    "whisper_wpm_pass": "low_narration_density",
    "qa_transcript_timestamps_valid": "invalid_transcript_timestamps",
}
_REVIEW_CHECKS = {
    video_quality.BLUR_SCORE_KEY: (video_quality.DEFAULT_BLUR_SCORE_LOW_MAX, "blurry"),
    video_quality.LIGHTING_SCORE_KEY: (
        video_quality.DEFAULT_LIGHTING_SCORE_LOW_MAX,
        "poor_lighting",
    ),
    video_quality.MOTION_SCORE_KEY: (
        video_quality.DEFAULT_MOTION_SCORE_LOW_MAX,
        "static_camera",
    ),
    "whisper_caption_count": (
        float(egocentric_qa.MIN_NARRATION_CAPTION_COUNT),
        "no_action_phrases",
    ),
}


@dataclass(frozen=True)
class ScreenResult:
    """Concise result printed after screening a video."""

    file_name: str
    status: str
    issues: str


def deliveries(
    dataset: VideoDataset,
    local_deliveries: list[LocalDelivery],
    force: bool = False,
) -> list[ScreenResult]:
    """Ingest and screen local deliveries."""
    for delivery in local_deliveries:
        dataset.add_videos_from_path(
            path=delivery.video_path.resolve(),
            embed=False,
            embed_frames=False,
            extract_frames=False,
        )

    videos = _videos_by_delivery(dataset=dataset, deliveries=local_deliveries)
    _write_provenance(dataset=dataset, deliveries=local_deliveries, videos=videos)
    pending = [video for video in videos if force or not _is_complete(video)]
    if pending:
        _run_checks(
            dataset=dataset,
            videos=pending,
            deliveries=local_deliveries,
        )
    return [_read_result(video) for video in videos]


def write_dataset_summary(dataset: VideoDataset) -> None:
    """Print aggregate verdict counts."""
    statuses = {"pass": 0, "review": 0, "fail": 0}
    for video in dataset:
        status = _metadata(video).get("automated_qa_status")
        if status in statuses:
            statuses[str(status)] += 1
    print(
        "Dataset status: "
        f"pass={statuses['pass']}, review={statuses['review']}, fail={statuses['fail']}"
    )


def _run_checks(
    dataset: VideoDataset,
    videos: list[VideoSample],
    deliveries: list[LocalDelivery],
) -> None:
    _set_complete(dataset=dataset, videos=videos, complete=False)
    _write_transcript_metadata(dataset=dataset, videos=videos, deliveries=deliveries)
    _score_quality(dataset=dataset, videos=videos)
    _write_technical_metadata(dataset=dataset, videos=videos)
    for video in videos:
        _write_verdict(video)
    _set_complete(dataset=dataset, videos=videos, complete=True)


def _write_transcript_metadata(
    dataset: VideoDataset,
    videos: list[VideoSample],
    deliveries: list[LocalDelivery],
) -> None:
    paths = {delivery.video_path.resolve(): delivery.transcript_path for delivery in deliveries}
    for video in videos:
        transcript_path = paths[Path(video.file_path_abs).resolve()]
        if transcript_path is None:
            continue
        duration_s = float(video.duration_s) if video.duration_s is not None else None
        transcript = whisper_transcript.load_whisper_transcript(
            transcript_path,
            caption_unit="narration_chunk",
            video_duration_s=duration_s,
        )
        segments = whisper_transcript.load_whisper_transcript(
            transcript_path,
            caption_unit="segment",
            video_duration_s=duration_s,
        )
        _replace_captions(dataset=dataset, video=video, transcript=transcript)
        words_per_minute = transcript.words_per_minute(duration_s=duration_s)
        metadata_resolver.bulk_update_metadata(
            dataset.session,
            [
                (
                    video.sample_id,
                    {
                        "whisper_language": transcript.language,
                        "whisper_language_probability": transcript.language_probability,
                        "whisper_word_count": transcript.word_count,
                        "whisper_words_per_minute": words_per_minute,
                        "whisper_wpm_pass": (
                            words_per_minute is not None
                            and words_per_minute >= egocentric_qa.MIN_NARRATION_WORDS_PER_MINUTE
                        ),
                        "whisper_caption_count": len(transcript.captions),
                        "whisper_caption_unit": "narration_chunk",
                        "whisper_speech_duration_s": transcript.speech_duration_s,
                        "whisper_silence_duration_s": transcript.silence_duration_s,
                        "whisper_silence_ratio": transcript.silence_ratio,
                        "whisper_silence_count": len(transcript.silences),
                        "qa_has_narration": transcript.word_count > 0,
                        "qa_is_english": egocentric_qa.is_english(language=transcript.language),
                        "qa_transcript_timestamps_valid": (
                            egocentric_qa.has_valid_caption_timestamps(
                                captions=segments.captions,
                                duration_s=duration_s,
                            )
                        ),
                        "expected_quality_label": _expected_label(video.file_name),
                    },
                )
            ],
        )


def _replace_captions(
    dataset: VideoDataset,
    video: VideoSample,
    transcript: whisper_transcript.WhisperTranscript,
) -> None:
    dataset.session.expire(video.sample_table, ["captions"])
    for caption in list(video.sample_table.captions):
        caption_resolver.delete_caption(session=dataset.session, sample_id=caption.sample_id)
    caption_resolver.create_many(
        session=dataset.session,
        parent_collection_id=video.collection_id,
        captions=[
            CaptionCreate(
                parent_sample_id=video.sample_id,
                text=caption.text,
                start_time_s=caption.start_time_s,
                end_time_s=caption.end_time_s,
            )
            for caption in transcript.captions
        ],
    )


def _score_quality(dataset: VideoDataset, videos: list[VideoSample]) -> None:
    filters = VideoFilter(
        sample_filter=SampleFilter(sample_ids=[video.sample_id for video in videos])
    )
    video_quality.compute_and_store_quality_metadata(
        session=dataset.session,
        collection_id=dataset.collection_id,
        filters=filters,
    )


def _write_technical_metadata(dataset: VideoDataset, videos: list[VideoSample]) -> None:
    updates: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in videos:
        duration_s = float(video.duration_s) if video.duration_s is not None else None
        updates.append(
            (
                video.sample_id,
                {
                    "qa_resolution_pass": egocentric_qa.has_minimum_1080p_resolution(
                        width=video.width,
                        height=video.height,
                    ),
                    "qa_duration_pass": egocentric_qa.has_valid_duration(duration_s=duration_s),
                    "qa_has_audio": egocentric_qa.has_audio_stream(video_path=video.file_path_abs),
                    "qa_orientation": egocentric_qa.get_orientation(
                        width=video.width,
                        height=video.height,
                    ),
                    "qa_media_format": Path(video.file_path_abs).suffix.lower().lstrip("."),
                    "qa_preferred_format": egocentric_qa.has_preferred_video_format(
                        video_path=video.file_path_abs
                    ),
                },
            )
        )
    metadata_resolver.bulk_update_metadata(dataset.session, updates)


def _write_verdict(video: VideoSample) -> None:
    metadata = _metadata(video)
    failures = [issue for key, issue in _REQUIRED_CHECKS.items() if metadata.get(key) is not True]
    review_issues = [
        issue
        for key, (threshold, issue) in _REVIEW_CHECKS.items()
        if isinstance((value := metadata.get(key)), (int, float)) and value < threshold
    ]
    status = "fail" if failures else "review" if review_issues else "pass"
    issues = [*failures, *review_issues]
    metadata_resolver.bulk_update_metadata(
        video.get_object_session(),
        [
            (
                video.sample_id,
                {
                    "qa_deterministic_pass": not failures,
                    "automated_qa_status": status,
                    "automated_qa_failures": ", ".join(failures),
                    "automated_qa_review_issues": ", ".join(review_issues),
                    "automated_qa_issues": ", ".join(issues),
                },
            )
        ],
    )


def _write_provenance(
    dataset: VideoDataset,
    deliveries: list[LocalDelivery],
    videos: list[VideoSample],
) -> None:
    by_path = {delivery.video_path.resolve(): delivery for delivery in deliveries}
    updates: list[tuple[UUID, Mapping[str, Any]]] = []
    for video in videos:
        delivery = by_path[Path(video.file_path_abs).resolve()]
        updates.append(
            (
                video.sample_id,
                {
                    "qa_source_bucket": delivery.bucket,
                    "qa_source_prefix": delivery.prefix,
                    "qa_source_stem": delivery.stem,
                    "qa_source_video_url": delivery.source_files[0],
                    "qa_source_files": list(delivery.source_files),
                },
            )
        )
    metadata_resolver.bulk_update_metadata(dataset.session, updates)


def _videos_by_delivery(
    dataset: VideoDataset,
    deliveries: list[LocalDelivery],
) -> list[VideoSample]:
    by_path = {Path(video.file_path_abs).resolve(): video for video in dataset}
    try:
        return [by_path[delivery.video_path.resolve()] for delivery in deliveries]
    except KeyError as error:
        raise RuntimeError(f"Video was not ingested: '{error.args[0]}'.") from error


def _set_complete(dataset: VideoDataset, videos: list[VideoSample], complete: bool) -> None:
    metadata_resolver.bulk_update_metadata(
        dataset.session,
        [(video.sample_id, {COMPLETE_KEY: complete}) for video in videos],
    )


def _is_complete(video: VideoSample) -> bool:
    return _metadata(video).get(COMPLETE_KEY) is True


def _metadata(video: VideoSample) -> dict[str, Any]:
    row = metadata_resolver.get_by_sample_id(
        session=video.get_object_session(),
        sample_id=video.sample_id,
    )
    return dict(row.data) if row is not None else {}


def _read_result(video: VideoSample) -> ScreenResult:
    metadata = _metadata(video)
    return ScreenResult(
        file_name=video.file_name,
        status=str(metadata.get("automated_qa_status")),
        issues=str(metadata.get("automated_qa_issues") or ""),
    )


def _expected_label(file_name: str) -> str:
    normalized = file_name.lower()
    if "accepted" in normalized:
        return "accepted"
    if "rejected" in normalized or "reject_" in normalized:
        return "rejected"
    return "unlabeled"
