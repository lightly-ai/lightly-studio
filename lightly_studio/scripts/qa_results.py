#!/usr/bin/env python3
"""Build and upload durable per-video QA result records."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from lightly_studio.resolvers import metadata_resolver

if TYPE_CHECKING or __package__:
    from scripts import qa_result_schema
else:
    import qa_result_schema

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

    from lightly_studio.core.video.video_dataset import VideoDataset
    from lightly_studio.core.video.video_sample import VideoSample
    from lightly_studio.models.caption import CaptionTable
    from scripts import qa_pull

DEFAULT_RESULTS_PREFIX = "automated_qa_results"
RESULT_SCHEMA_VERSION = qa_result_schema.RESULT_SCHEMA_VERSION
PIPELINE_COMPLETE_KEY = "qa_pipeline_complete"


def upload_result_records(
    client: storage.Client,
    dataset: VideoDataset,
    triplets: list[qa_pull.LocalTriplet],
    results_prefix: str = DEFAULT_RESULTS_PREFIX,
) -> list[str]:
    """Upload one complete QA record per triplet to its source bucket.

    Existing records are replaced so a forced reprocessing run can publish the latest
    database metadata. Records are uploaded before local cleanup; an upload failure
    therefore leaves the batch files available for retry.

    Returns:
        The uploaded ``gs://`` URLs in input order.
    """
    records = build_result_records(
        dataset=dataset,
        triplets=triplets,
        results_prefix=results_prefix,
    )
    uploaded_urls: list[str] = []
    for triplet, object_name, record in records:
        client.bucket(triplet.bucket).blob(object_name).upload_from_string(
            json.dumps(_json_safe(value=record), indent=2, allow_nan=False),
            content_type="application/json",
        )
        uploaded_urls.append(f"gs://{triplet.bucket}/{object_name}")
    return uploaded_urls


def filter_unpublished_triplets(
    client: storage.Client,
    triplets: list[qa_pull.RemoteTriplet],
    results_prefix: str = DEFAULT_RESULTS_PREFIX,
) -> list[qa_pull.RemoteTriplet]:
    """Return deliveries with no existing result record.

    Existing object names are listed once per bucket so cron runs do not download and
    reopen every historical video merely to discover that it is already complete.
    """
    normalized_prefix = _normalize_results_prefix(results_prefix=results_prefix)
    existing_by_bucket: dict[str, set[str]] = {}
    for triplet in triplets:
        if triplet.bucket in existing_by_bucket:
            continue
        blobs = client.list_blobs(triplet.bucket, prefix=f"{normalized_prefix}/")
        existing_by_bucket[triplet.bucket] = {blob.name for blob in blobs}
    return [
        triplet
        for triplet in triplets
        if result_object_name(triplet=triplet, results_prefix=normalized_prefix)
        not in existing_by_bucket[triplet.bucket]
    ]


def build_result_records(
    dataset: VideoDataset,
    triplets: list[qa_pull.LocalTriplet],
    results_prefix: str = DEFAULT_RESULTS_PREFIX,
) -> list[tuple[qa_pull.LocalTriplet, str, dict[str, Any]]]:
    """Build complete result records without writing to GCS."""
    videos_by_path = {Path(video.file_path_abs).resolve(): video for video in dataset}
    records = []
    for triplet in triplets:
        video = videos_by_path.get(triplet.video_path.resolve())
        if video is None:
            raise RuntimeError(f"Cannot write result for unindexed video: '{triplet.video_path}'.")
        metadata_row = metadata_resolver.get_by_sample_id(
            session=dataset.session,
            sample_id=video.sample_id,
        )
        metadata = dict(metadata_row.data) if metadata_row is not None else {}
        if metadata.get(PIPELINE_COMPLETE_KEY) is not True:
            raise RuntimeError(f"Cannot write incomplete QA result for '{video.file_name}'.")
        dataset.session.expire(video.sample_table, ["captions"])

        object_name = result_object_name(triplet=triplet, results_prefix=results_prefix)
        result_url = f"gs://{triplet.bucket}/{object_name}"
        records.append(
            (
                triplet,
                object_name,
                _build_record(
                    video=video,
                    triplet=triplet,
                    metadata=metadata,
                    captions=list(video.sample_table.captions),
                    result_url=result_url,
                ),
            )
        )
    return records


def result_object_name(
    triplet: qa_pull.LocalTriplet | qa_pull.RemoteTriplet,
    results_prefix: str,
) -> str:
    """Return ``automated_qa_results/{stem_name}_results.json`` safely.

    The result is written flat under the prefix using only the delivery's file name,
    not its source subfolders.
    """
    normalized_prefix = _normalize_results_prefix(results_prefix=results_prefix)
    stem = PurePosixPath(triplet.stem)
    if stem.is_absolute() or ".." in stem.parts:
        raise ValueError(f"Invalid delivery stem for result object: '{triplet.stem}'.")
    return f"{normalized_prefix}/{stem.name}_results.json"


def _normalize_results_prefix(results_prefix: str) -> str:
    normalized_prefix = results_prefix.strip("/")
    if not normalized_prefix:
        raise ValueError("results_prefix must not be empty.")
    return normalized_prefix


def _build_record(
    video: VideoSample,
    triplet: qa_pull.LocalTriplet,
    metadata: dict[str, Any],
    captions: list[CaptionTable],
    result_url: str,
) -> dict[str, Any]:
    return {
        "verdict": qa_result_schema.build_verdict(metadata=metadata),
        "schema_version": qa_result_schema.RESULT_SCHEMA_VERSION,
        "policy_version": qa_result_schema.QA_POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result_url": result_url,
        "source": {
            "bucket": triplet.bucket,
            "prefix": triplet.prefix,
            "stem": triplet.stem,
            "video_url": triplet.source_files[0],
            "files": list(triplet.source_files),
        },
        "video": {
            "sample_id": str(video.sample_id),
            "file_name": video.file_name,
            "file_path_abs": video.file_path_abs,
            "width": video.width,
            "height": video.height,
            "duration_s": video.duration_s,
            "fps": video.fps,
        },
        "checks": qa_result_schema.build_checks(
            metadata=metadata,
            width=video.width,
            height=video.height,
            duration_s=video.duration_s,
        ),
        "metrics": qa_result_schema.build_metrics(metadata=metadata),
        "narration_chunks": [_build_caption_record(caption=caption) for caption in captions],
    }


def _build_caption_record(caption: CaptionTable) -> dict[str, Any]:
    span = caption.temporal_span_details
    metadata = dict(caption.metadata_dict.data) if caption.metadata_dict is not None else {}
    return {
        "sample_id": str(caption.sample_id),
        "text": caption.text,
        "start_time_s": span.start_time_s if span is not None else None,
        "end_time_s": span.end_time_s if span is not None else None,
        "metadata": metadata,
    }


def _json_safe(value: Any) -> Any:
    """Return a recursively strict-JSON-compatible value."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(value=item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(value=item) for item in value]
    item_method = getattr(value, "item", None)
    if callable(item_method):
        return _json_safe(value=item_method())
    raise TypeError(f"Value of type {type(value).__name__} is not JSON serializable.")
