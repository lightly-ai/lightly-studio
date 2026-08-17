"""GCS discovery and local file handling for automatic QA."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

DEFAULT_PROJECT = "egocentricdatahouse"
DEFAULT_BUCKET_SUFFIX = "-qa"
DEFAULT_WORK_PREFIXES = ("review", "pool")
VIDEO_SUFFIX = ".mp4"
TRANSCRIPT_SUFFIXES = (
    "_transcript.json",
    ".transcript.json",
    ".transcripts.json",
    "_transcripts.json",
)
METADATA_SUFFIXES = ("_metadata.json", ".metadata.json")

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RemoteDelivery:
    """Files belonging to one delivery in GCS."""

    bucket: str
    prefix: str
    stem: str
    files: tuple[str, ...]


@dataclass(frozen=True)
class LocalDelivery:
    """A downloaded delivery and its local files."""

    bucket: str
    prefix: str
    stem: str
    video_path: Path
    transcript_path: Path | None
    source_files: tuple[str, ...]
    local_files: tuple[Path, ...]


def create_client(project: str) -> storage.Client:
    """Create a Google Cloud Storage client."""
    from google.cloud import storage  # noqa: PLC0415

    return storage.Client(project=project)


def discover(
    client: storage.Client,
    buckets: tuple[str, ...] = (),
    bucket_suffix: str = DEFAULT_BUCKET_SUFFIX,
    prefixes: tuple[str, ...] = DEFAULT_WORK_PREFIXES,
) -> list[RemoteDelivery]:
    """Discover video deliveries in the requested buckets and prefixes."""
    bucket_names = buckets or tuple(
        sorted(
            bucket.name for bucket in client.list_buckets() if bucket.name.endswith(bucket_suffix)
        )
    )
    deliveries = [
        delivery
        for bucket in bucket_names
        for prefix in prefixes
        for delivery in _list_deliveries(client=client, bucket=bucket, prefix=prefix)
    ]
    return _deduplicate(deliveries)


def download(
    client: storage.Client,
    deliveries: list[RemoteDelivery],
    destination: Path,
) -> list[LocalDelivery]:
    """Download deliveries into a local workspace."""
    return [
        _download_one(client=client, delivery=delivery, destination=destination)
        for delivery in deliveries
    ]


def cleanup(deliveries: list[LocalDelivery], destination: Path) -> int:
    """Delete tracked delivery files below the destination."""
    root = destination.resolve()
    paths = {path.resolve() for delivery in deliveries for path in delivery.local_files}
    if outside := [path for path in paths if not path.is_relative_to(root)]:
        raise ValueError(f"Refusing to clean up path outside destination: '{outside[0]}'.")
    for path in paths:
        path.unlink(missing_ok=True)
    return len(paths)


def _list_deliveries(
    client: storage.Client,
    bucket: str,
    prefix: str,
) -> list[RemoteDelivery]:
    normalized_prefix = prefix.strip("/")
    root = f"{normalized_prefix}/"
    names = sorted(
        blob.name for blob in client.list_blobs(bucket, prefix=root) if not blob.name.endswith("/")
    )
    by_relative = {name.removeprefix(root): name for name in names}
    deliveries = []
    for relative, video_name in by_relative.items():
        if not relative.lower().endswith(VIDEO_SUFFIX):
            continue
        stem = relative[: -len(VIDEO_SUFFIX)]
        companions = [
            name
            for suffixes in (TRANSCRIPT_SUFFIXES, METADATA_SUFFIXES)
            for suffix in suffixes
            if (name := by_relative.get(stem + suffix)) is not None
        ]
        object_names = (video_name, *companions)
        deliveries.append(
            RemoteDelivery(
                bucket=bucket,
                prefix=normalized_prefix,
                stem=stem,
                files=tuple(f"gs://{bucket}/{name}" for name in object_names),
            )
        )
    return deliveries


def _download_one(
    client: storage.Client,
    delivery: RemoteDelivery,
    destination: Path,
) -> LocalDelivery:
    local_dir = _local_directory(destination=destination, delivery=delivery)
    local_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for url in delivery.files:
        bucket, name = split_gcs_url(url)
        path = local_dir / PurePosixPath(name).name
        client.bucket(bucket).blob(name).download_to_filename(str(path))
        paths.append(path)
    return LocalDelivery(
        bucket=delivery.bucket,
        prefix=delivery.prefix,
        stem=delivery.stem,
        video_path=paths[0],
        transcript_path=_find_companion(paths=paths, suffixes=TRANSCRIPT_SUFFIXES),
        source_files=delivery.files,
        local_files=tuple(paths),
    )


def split_gcs_url(url: str) -> tuple[str, str]:
    """Split a GCS object URL into its bucket and object name."""
    bucket, separator, name = url.removeprefix("gs://").partition("/")
    if not url.startswith("gs://") or not separator or not bucket or not name:
        raise ValueError(f"Not a GCS object URL: '{url}'.")
    return bucket, name


def _find_companion(paths: list[Path], suffixes: tuple[str, ...]) -> Path | None:
    return next((path for path in paths if path.name.endswith(suffixes)), None)


def _deduplicate(deliveries: list[RemoteDelivery]) -> list[RemoteDelivery]:
    unique: dict[tuple[str, str], RemoteDelivery] = {}
    for delivery in deliveries:
        identity = (delivery.bucket, delivery.stem)
        if previous := unique.get(identity):
            logger.warning(
                "Skipping duplicate %s/%s in %s; using %s.",
                delivery.bucket,
                delivery.stem,
                delivery.prefix,
                previous.prefix,
            )
            continue
        unique[identity] = delivery
    return list(unique.values())


def _local_directory(destination: Path, delivery: RemoteDelivery) -> Path:
    root = destination.resolve()
    path = (root / delivery.bucket / delivery.stem).resolve()
    if not path.is_relative_to(root):
        raise ValueError(f"Delivery stem escapes destination: '{delivery.stem}'.")
    return path
