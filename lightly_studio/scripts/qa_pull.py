#!/usr/bin/env python3
"""Pull egocentric deliveries from the pool and review prefixes to local disk.

Step one of the QA pipeline. Discover video-bearing deliveries across the ``review``
and ``pool`` prefixes of every ``-qa`` bucket, then download each delivery into its own
local folder so a later QA stage can ingest one video with its optional companions at a
time. Nothing here evaluates quality; it only moves bytes down from GCS.

The triplet definition and the GCS helpers are reused from ``sample_gcs_review`` so the
notion of a "complete triplet" stays single-sourced across the sampler and this puller.
"""

# Reuse the sampler's private GCS helpers so the triplet grouping stays in one place.
# ruff: noqa: SLF001
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

if TYPE_CHECKING or __package__:
    from scripts import sample_gcs_review as sampler
else:
    import sample_gcs_review as sampler

DEFAULT_WORK_PREFIXES = ("review", "pool")


@dataclass(frozen=True)
class RemoteTriplet:
    """A complete triplet located in GCS, not yet downloaded."""

    bucket: str
    prefix: str
    stem: str
    files: tuple[str, ...]  # full gs:// URLs, video first

    @property
    def video_url(self) -> str:
        """Return the video's gs:// URL (the first file in the group)."""
        return self.files[0]


@dataclass(frozen=True)
class LocalTriplet:
    """A delivery downloaded to local disk, one folder per video.

    ``transcript_path`` is ``None`` when the video shipped without a transcript; the
    transcription step (``qa_transcribe``) fills it in with faster-whisper. Metadata is
    likewise optional so a video that arrives alone can still be pulled and processed.
    """

    bucket: str
    prefix: str
    stem: str
    video_path: Path
    transcript_path: Path | None
    metadata_path: Path | None
    source_files: tuple[str, ...]
    local_files: tuple[Path, ...]


def discover_triplets(
    client: storage.Client,
    buckets: tuple[str, ...],
    bucket_suffix: str,
    work_prefixes: tuple[str, ...],
) -> list[RemoteTriplet]:
    """List every complete triplet under the work prefixes of the target buckets.

    Args:
        client: Authenticated storage client.
        buckets: Explicit buckets to scan. Empty means discover by ``bucket_suffix``.
        bucket_suffix: Suffix used to auto-discover buckets when none are given.
        work_prefixes: Prefixes to pull from, e.g. ``("review", "pool")``.

    Returns:
        Every video-bearing delivery found, in listing order. A missing transcript does
        not exclude a delivery: the transcription step generates one afterwards. Stray
        non-video objects are ignored (they never form a group).
    """
    target_buckets = buckets or tuple(sampler._list_buckets(client=client, suffix=bucket_suffix))
    triplets: list[RemoteTriplet] = []
    for bucket in target_buckets:
        for prefix in work_prefixes:
            root = sampler._gcs_root(bucket=bucket, prefix=prefix)
            objects = sampler._list_objects(client=client, bucket=bucket, prefix=prefix)
            groups, _ = sampler.group_source_objects(objects=objects, source_root=root)
            for group in groups:
                triplets.append(
                    RemoteTriplet(
                        bucket=bucket,
                        prefix=prefix,
                        stem=group.stem,
                        files=tuple(group.files),
                    )
                )
    _validate_unique_triplets(triplets=triplets)
    return triplets


def pull_triplets(  # noqa: PLR0913  parameters mirror the discovery + download knobs.
    client: storage.Client,
    destination: Path,
    buckets: tuple[str, ...] = (),
    bucket_suffix: str = sampler.DEFAULT_BUCKET_SUFFIX,
    work_prefixes: tuple[str, ...] = DEFAULT_WORK_PREFIXES,
    max_videos: int | None = None,
) -> list[LocalTriplet]:
    """Discover and download complete triplets into per-video folders under ``destination``.

    Args:
        client: Authenticated storage client.
        destination: Local root the triplets are downloaded under.
        buckets: Explicit buckets to pull from. Empty means discover by suffix.
        bucket_suffix: Suffix used to auto-discover buckets when none are given.
        work_prefixes: Prefixes to pull from, e.g. ``("review", "pool")``.
        max_videos: Stop after downloading this many triplets. ``None`` pulls all.

    Returns:
        The downloaded triplets with their resolved local paths.
    """
    remote = discover_triplets(
        client=client,
        buckets=buckets,
        bucket_suffix=bucket_suffix,
        work_prefixes=work_prefixes,
    )
    if max_videos is not None:
        remote = remote[:max_videos]

    return download_triplets(client=client, triplets=remote, destination=destination)


def download_triplets(
    client: storage.Client,
    triplets: list[RemoteTriplet],
    destination: Path,
) -> list[LocalTriplet]:
    """Download already-discovered triplets without listing GCS again.

    This entry point lets the orchestrator keep local disk usage bounded by downloading
    one batch of the remote manifest at a time.
    """
    return [
        _download_triplet(client=client, triplet=triplet, destination=destination)
        for triplet in triplets
    ]


def cleanup_triplets(triplets: list[LocalTriplet], destination: Path) -> int:
    """Delete only the files created for ``triplets`` below ``destination``.

    Unrelated files and directories are preserved. The containment check protects
    callers from deleting paths outside the configured download root.

    Returns:
        The number of files deleted.
    """
    destination_resolved = destination.resolve()
    paths = {path.resolve() for triplet in triplets for path in triplet.local_files}
    for path in paths:
        if not path.is_relative_to(destination_resolved):
            raise ValueError(f"Refusing to clean up path outside destination: '{path}'.")

    deleted = 0
    for path in paths:
        if path.is_file():
            path.unlink()
            deleted += 1
    return deleted


def _download_triplet(
    client: storage.Client, triplet: RemoteTriplet, destination: Path
) -> LocalTriplet:
    """Download one triplet into ``destination/{bucket}/{stem}`` and resolve its parts.

    The stem is unique per video, so each triplet gets its own folder and the folder
    holds exactly one video, which is what a per-video QA ingest expects.
    """
    local_dir = _resolve_local_dir(destination=destination, triplet=triplet)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_by_url: dict[str, Path] = {}
    for url in triplet.files:
        _, name = sampler._split_gcs_url(url)
        target = local_dir / Path(name).name
        _blob(client=client, url=url).download_to_filename(str(target))
        local_by_url[url] = target

    return LocalTriplet(
        bucket=triplet.bucket,
        prefix=triplet.prefix,
        stem=triplet.stem,
        video_path=local_by_url[triplet.video_url],
        transcript_path=_find_companion(local_by_url, sampler.TRANSCRIPT_SUFFIXES),
        metadata_path=_find_companion(local_by_url, sampler.METADATA_SUFFIXES),
        source_files=triplet.files,
        local_files=tuple(local_by_url.values()),
    )


def _find_companion(local_by_url: dict[str, Path], suffixes: tuple[str, ...]) -> Path | None:
    """Return the one downloaded file whose name ends with any of ``suffixes``, if present."""
    for path in local_by_url.values():
        if path.name.endswith(suffixes):
            return path
    return None


def _blob(client: storage.Client, url: str) -> storage.Blob:
    bucket_name, name = sampler._split_gcs_url(url)
    return client.bucket(bucket_name).blob(name)


def _validate_unique_triplets(triplets: list[RemoteTriplet]) -> None:
    """Reject ambiguous deliveries that would share a stable local path."""
    by_identity: dict[tuple[str, str], RemoteTriplet] = {}
    for triplet in triplets:
        identity = (triplet.bucket, triplet.stem)
        previous = by_identity.get(identity)
        if previous is not None:
            raise ValueError(
                "Delivery appears under multiple work prefixes: "
                f"{triplet.bucket}/{triplet.stem} ({previous.prefix}, {triplet.prefix})."
            )
        by_identity[identity] = triplet


def _resolve_local_dir(destination: Path, triplet: RemoteTriplet) -> Path:
    """Resolve a delivery directory and reject object stems that escape the root."""
    destination_resolved = destination.resolve()
    local_dir = (destination_resolved / triplet.bucket / triplet.stem).resolve()
    if not local_dir.is_relative_to(destination_resolved):
        raise ValueError(f"Delivery stem escapes destination: '{triplet.stem}'.")
    return local_dir
