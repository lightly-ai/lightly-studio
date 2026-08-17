"""Build and upload automatic QA result records."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, Any

from auto_qa import schema, screen
from auto_qa.storage import LocalDelivery, RemoteDelivery
from lightly_studio.resolvers import metadata_resolver

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

    from lightly_studio.core.video.video_dataset import VideoDataset
    from lightly_studio.core.video.video_sample import VideoSample
    from lightly_studio.models.caption import CaptionTable

DEFAULT_PREFIX = "automated_qa_results"


def unpublished(
    client: storage.Client,
    deliveries: list[RemoteDelivery],
    prefix: str = DEFAULT_PREFIX,
) -> list[RemoteDelivery]:
    """Return deliveries without a published result."""
    normalized_prefix = _normalize_prefix(prefix)
    existing = {
        bucket: {blob.name for blob in client.list_blobs(bucket, prefix=f"{normalized_prefix}/")}
        for bucket in dict.fromkeys(delivery.bucket for delivery in deliveries)
    }
    return [
        delivery
        for delivery in deliveries
        if object_name(delivery=delivery, prefix=normalized_prefix) not in existing[delivery.bucket]
    ]


def upload(
    client: storage.Client,
    dataset: VideoDataset,
    deliveries: list[LocalDelivery],
    prefix: str = DEFAULT_PREFIX,
) -> list[str]:
    """Upload one result record for each delivery."""
    uploaded = []
    for delivery, name, record in build(dataset=dataset, deliveries=deliveries, prefix=prefix):
        client.bucket(delivery.bucket).blob(name).upload_from_string(
            json.dumps(_json_safe(record), indent=2, allow_nan=False),
            content_type="application/json",
        )
        uploaded.append(f"gs://{delivery.bucket}/{name}")
    return uploaded


def build(
    dataset: VideoDataset,
    deliveries: list[LocalDelivery],
    prefix: str = DEFAULT_PREFIX,
) -> list[tuple[LocalDelivery, str, dict[str, Any]]]:
    """Build result records without uploading them."""
    videos = {Path(video.file_path_abs).resolve(): video for video in dataset}
    records = []
    for delivery in deliveries:
        video = videos.get(delivery.video_path.resolve())
        if video is None:
            raise RuntimeError(f"Cannot publish unindexed video: '{delivery.video_path}'.")
        metadata = _metadata(dataset=dataset, video=video)
        if metadata.get(screen.COMPLETE_KEY) is not True:
            raise RuntimeError(f"Cannot publish incomplete QA result for '{video.file_name}'.")
        dataset.session.expire(video.sample_table, ["captions"])
        name = object_name(delivery=delivery, prefix=prefix)
        records.append(
            (
                delivery,
                name,
                _record(
                    delivery=delivery,
                    video=video,
                    metadata=metadata,
                    captions=list(video.sample_table.captions),
                    url=f"gs://{delivery.bucket}/{name}",
                ),
            )
        )
    return records


def object_name(delivery: LocalDelivery | RemoteDelivery, prefix: str) -> str:
    """Return the result object name for a delivery."""
    normalized_prefix = _normalize_prefix(prefix)
    stem = PurePosixPath(delivery.stem)
    if stem.is_absolute() or ".." in stem.parts:
        raise ValueError(f"Invalid delivery stem for result object: '{delivery.stem}'.")
    return f"{normalized_prefix}/{stem.name}_results.json"


def _record(
    delivery: LocalDelivery,
    video: VideoSample,
    metadata: dict[str, Any],
    captions: list[CaptionTable],
    url: str,
) -> dict[str, Any]:
    return {
        "verdict": schema.build_verdict(metadata),
        "schema_version": schema.RESULT_SCHEMA_VERSION,
        "policy_version": schema.QA_POLICY_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "result_url": url,
        "source": {
            "bucket": delivery.bucket,
            "prefix": delivery.prefix,
            "stem": delivery.stem,
            "video_url": delivery.source_files[0],
            "files": list(delivery.source_files),
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
        "checks": schema.build_checks(
            metadata=metadata,
            width=video.width,
            height=video.height,
            duration_s=video.duration_s,
        ),
        "metrics": schema.build_metrics(metadata),
        "narration_chunks": [_caption(caption) for caption in captions],
    }


def _caption(caption: CaptionTable) -> dict[str, Any]:
    span = caption.temporal_span_details
    metadata = dict(caption.metadata_dict.data) if caption.metadata_dict is not None else {}
    return {
        "sample_id": str(caption.sample_id),
        "text": caption.text,
        "start_time_s": span.start_time_s if span is not None else None,
        "end_time_s": span.end_time_s if span is not None else None,
        "metadata": metadata,
    }


def _normalize_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    if not normalized:
        raise ValueError("results prefix must not be empty.")
    return normalized


def _metadata(dataset: VideoDataset, video: VideoSample) -> dict[str, Any]:
    row = metadata_resolver.get_by_sample_id(session=dataset.session, sample_id=video.sample_id)
    return dict(row.data) if row is not None else {}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    item = getattr(value, "item", None)
    if callable(item):
        return _json_safe(item())
    raise TypeError(f"Cannot serialize {type(value).__name__} to JSON.")
