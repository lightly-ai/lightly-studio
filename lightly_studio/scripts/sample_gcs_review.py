#!/usr/bin/env python3
"""Partition a GCS source prefix into review and pool, one video at a time.

Each delivery is a video (``{stem}.mp4``) plus companion files that share its stem
(a transcript and a metadata JSON, with either an underscore or dot separator, e.g.
``{stem}_transcript.json`` or ``{stem}.transcript.json``). Sampling happens per video:
a reproducible random sample of the shippable videos is moved to ``review`` and the rest
to ``pool``, keeping every video's companion files together. A delivery ships only when it
is complete: the video, its transcript, and its metadata companion are all present. Any
group missing a companion, along with stray files that belong to no video, is moved to
``incomplete``. Objects are moved out of ``source`` so a later run only
ever sees files that arrived since the previous run: originals are never reconsidered and
re-uploads are a fresh batch.

Multiple buckets are processed in one run. By default every bucket whose name ends
with ``--bucket-suffix`` (``-qa``) is discovered, so newly added QA buckets are picked
up automatically. Pass ``--bucket`` one or more times to target an explicit list instead.

The command is a dry run unless ``--apply`` is provided. Storage access uses the
``google-cloud-storage`` client, so run with the ``cloud-storage`` extra installed.

Examples:
    uv run --extra cloud-storage python scripts/sample_gcs_review.py
    uv run --extra cloud-storage python scripts/sample_gcs_review.py --apply
"""

from __future__ import annotations

import argparse
import math
import random
import re
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

DEFAULT_BUCKET_SUFFIX = "-qa"
DEFAULT_FRACTION = 0.33
DEFAULT_INCOMPLETE_PREFIX = "incomplete"
DEFAULT_POOL_PREFIX = "pool"
DEFAULT_PROJECT = "egocentricdatahouse"
DEFAULT_REVIEW_PREFIX = "review"
DEFAULT_SEED = 42
DEFAULT_SOURCE_PREFIX = "source"
DEFAULT_WORKERS = 8

VIDEO_SUFFIX = ".mp4"
# Vendors separate the companion kind with either an underscore or a dot, e.g. both
# ``clip_transcript.json`` and ``clip.transcript.json`` occur across delivery buckets.
# A companion kind is present when any of its suffix variants is found.
TRANSCRIPT_SUFFIXES = (
    "_transcript.json",
    ".transcript.json",
    ".transcripts.json",
    "_transcripts.json",
)
METADATA_SUFFIXES = ("_metadata.json", ".metadata.json")
COMPANION_SUFFIX_GROUPS = (TRANSCRIPT_SUFFIXES, METADATA_SUFFIXES)


def main() -> None:
    """Sample every requested bucket per the command-line arguments."""
    args = _parse_args()
    client = _storage_client(project=args.project)
    buckets = args.bucket or _list_buckets(client=client, suffix=args.bucket_suffix)
    if not buckets:
        print(f"No buckets matched suffix {args.bucket_suffix!r}.")
        return

    for bucket in buckets:
        print(f"\n=== {bucket} ===")
        _process_bucket(client=client, bucket=bucket, args=args)


def _process_bucket(client: storage.Client, bucket: str, args: argparse.Namespace) -> None:
    source_root = _gcs_root(bucket=bucket, prefix=args.source_prefix)
    review_root = _gcs_root(bucket=bucket, prefix=args.review_prefix)
    pool_root = _gcs_root(bucket=bucket, prefix=args.pool_prefix)
    incomplete_root = _gcs_root(bucket=bucket, prefix=args.incomplete_prefix)

    objects = _list_objects(client=client, bucket=bucket, prefix=args.source_prefix)
    groups, unmatched = group_source_objects(objects=objects, source_root=source_root)
    shippable = [group for group in groups if group.is_shippable]
    not_shippable = [group for group in groups if not group.is_shippable]

    selected = set(
        select_sample(
            objects=[group.stem for group in shippable],
            fraction=args.fraction,
            seed=args.seed,
        )
    )

    # Split into two phases so ``--pause`` can move review first, let the caller
    # validate it, then move the rest (pool + incomplete) on confirmation.
    review_moves: list[tuple[str, str]] = []
    rest_moves: list[tuple[str, str]] = []
    for group in shippable:
        if group.stem in selected:
            review_moves += [
                (file, destination_url(file, source_root, review_root)) for file in group.files
            ]
        else:
            rest_moves += [
                (file, destination_url(file, source_root, pool_root)) for file in group.files
            ]
    quarantine = unmatched + [file for group in not_shippable for file in group.files]
    rest_moves += [
        (file, destination_url(file, source_root, incomplete_root)) for file in quarantine
    ]

    review_count = len(selected)
    pool_count = len(shippable) - review_count
    print(
        f"{len(shippable)} shippable videos -> {review_count} review ({args.fraction:.1%}), "
        f"{pool_count} pool; {len(not_shippable)} unshippable group(s), "
        f"{len(unmatched)} stray file(s) -> incomplete."
    )
    for source, destination in review_moves + rest_moves:
        print(f"{source} -> {destination}")

    if not review_moves and not rest_moves:
        return
    if not args.apply:
        print("Dry run only. Re-run with --apply to move these objects.")
        return

    if review_moves:
        _move_objects(client=client, moves=review_moves, workers=args.workers)
        print(f"Moved {review_count} video(s) to gs://{bucket}/{args.review_prefix}/.")
    if args.pause and rest_moves:
        input(
            f"Validate gs://{bucket}/{args.review_prefix}/, then press Enter to move the "
            f"remaining {pool_count} to pool and {len(quarantine)} to incomplete... "
        )
    if rest_moves:
        _move_objects(client=client, moves=rest_moves, workers=args.workers)
    print(
        f"Moved {review_count} video(s) to review, {pool_count} to pool, "
        f"{len(quarantine)} file(s) to incomplete."
    )


def select_sample(objects: Sequence[str], fraction: float, seed: int) -> list[str]:
    """Select a reproducible sample, rounded up to a whole object.

    Args:
        objects: GCS object URLs to sample.
        fraction: Fraction to select. Must be greater than zero and at most one.
        seed: Random seed used for reproducible selection.

    Returns:
        Selected object URLs in sorted order.

    Raises:
        ValueError: If the fraction is outside the supported range.
    """
    if not 0 < fraction <= 1:
        raise ValueError("fraction must be greater than zero and at most one")
    if not objects:
        return []

    sample_size = math.ceil(len(objects) * fraction)
    selected = random.Random(seed).sample(sorted(objects), k=sample_size)
    return sorted(selected)


_INVALID_NAME_CHARS = re.compile(r"[^0-9a-zA-Z._-]+")


def _sanitize_relative(relative: str) -> str:
    """Coerce each path segment to ``[0-9a-zA-Z._-]+`` so moved objects have valid names.

    Segments are coerced independently to keep the ``/`` folder structure. Coercion is
    deterministic per stem, so a video and its companions stay grouped after the move.
    """
    return "/".join(_INVALID_NAME_CHARS.sub("", segment) for segment in relative.split("/"))


def destination_url(source: str, source_root: str, destination_root: str) -> str:
    """Map a source object URL to the equivalent path below a destination prefix.

    Args:
        source: Full source object URL.
        source_root: Source prefix URL ending with a slash.
        destination_root: Destination prefix URL ending with a slash.

    Returns:
        Full destination object URL.

    Raises:
        ValueError: If the object is not below the source prefix.
    """
    if not source.startswith(source_root):
        raise ValueError(f"Object is outside the source prefix: {source}")
    relative = _sanitize_relative(source.removeprefix(source_root))
    return f"{destination_root}{relative}"


@dataclass
class VideoGroup:
    """A video and the delivery files that share its stem.

    Attributes:
        stem: Relative path under source without the video extension.
        files: Full object URLs in the group, video first, in listing order.
        is_complete: Whether every required companion file is present.
    """

    stem: str
    files: list[str]
    is_complete: bool

    @property
    def has_video(self) -> bool:
        """Return whether the delivery includes the video file."""
        return any(file.lower().endswith(VIDEO_SUFFIX) for file in self.files)

    @property
    def has_metadata(self) -> bool:
        """Return whether the delivery includes a metadata companion."""
        return any(file.endswith(METADATA_SUFFIXES) for file in self.files)

    @property
    def has_transcript(self) -> bool:
        """Return whether the delivery includes a transcript companion."""
        return any(file.endswith(TRANSCRIPT_SUFFIXES) for file in self.files)

    @property
    def is_shippable(self) -> bool:
        """Return whether the delivery is eligible for review/pool sampling.

        A delivery ships only when it is complete: the video, its transcript, and its
        metadata companion are all present. Any group missing a companion is quarantined
        to ``incomplete`` rather than sampled.
        """
        return self.has_video and self.has_transcript and self.has_metadata


def group_source_objects(
    objects: Sequence[str], source_root: str
) -> tuple[list[VideoGroup], list[str]]:
    """Group source objects into per-video delivery sets.

    Each video (``{stem}.mp4``) becomes a group. Companion files that share the
    stem (a transcript and a metadata JSON, in either the underscore or dot form)
    are attached to it, and the group is complete when both kinds are present. A
    kind is satisfied by any of its suffix variants. Objects that belong to no
    video group (orphan companions, stray files) are returned separately so the
    caller can quarantine them.

    Args:
        objects: Full source object URLs.
        source_root: Source prefix URL ending with a slash.

    Returns:
        A tuple of (video groups sorted by stem, unmatched object URLs sorted).
    """
    by_relative = {source.removeprefix(source_root): source for source in objects}
    grouped: set[str] = set()
    groups: list[VideoGroup] = []

    for relative in sorted(by_relative):
        if not relative.lower().endswith(VIDEO_SUFFIX):
            continue
        stem = relative[: -len(VIDEO_SUFFIX)]
        present = [relative]
        is_complete = True
        for suffix_variants in COMPANION_SUFFIX_GROUPS:
            matches = [stem + suffix for suffix in suffix_variants if stem + suffix in by_relative]
            present.extend(matches)
            if not matches:
                is_complete = False
        grouped.update(present)
        groups.append(
            VideoGroup(
                stem=stem,
                files=[by_relative[name] for name in present],
                is_complete=is_complete,
            )
        )

    unmatched = sorted(
        source for relative, source in by_relative.items() if relative not in grouped
    )
    return groups, unmatched


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument(
        "--bucket",
        action="append",
        help="Bucket to process. Repeatable. Defaults to discovery by --bucket-suffix.",
    )
    parser.add_argument("--bucket-suffix", default=DEFAULT_BUCKET_SUFFIX)
    parser.add_argument("--source-prefix", default=DEFAULT_SOURCE_PREFIX)
    parser.add_argument("--review-prefix", default=DEFAULT_REVIEW_PREFIX)
    parser.add_argument("--pool-prefix", default=DEFAULT_POOL_PREFIX)
    parser.add_argument("--incomplete-prefix", default=DEFAULT_INCOMPLETE_PREFIX)
    parser.add_argument("--fraction", type=float, default=DEFAULT_FRACTION)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move the objects. Without this flag, only print the plan.",
    )
    parser.add_argument(
        "--pause",
        action="store_true",
        help="After moving review, wait for Enter before moving the rest to pool/incomplete.",
    )
    return parser.parse_args()


def _gcs_root(bucket: str, prefix: str) -> str:
    normalized_prefix = prefix.strip("/")
    if not normalized_prefix:
        raise ValueError("prefix must not be empty")
    return f"gs://{bucket}/{normalized_prefix}/"


def _storage_client(project: str) -> storage.Client:
    # Imported lazily so the module imports without the optional cloud-storage extra.
    from google.cloud import storage  # noqa: PLC0415

    return storage.Client(project=project)


def _list_buckets(client: storage.Client, suffix: str) -> list[str]:
    return sorted(bucket.name for bucket in client.list_buckets() if bucket.name.endswith(suffix))


def _list_objects(client: storage.Client, bucket: str, prefix: str) -> list[str]:
    normalized_prefix = prefix.strip("/") + "/"
    blobs = client.list_blobs(bucket, prefix=normalized_prefix)
    return sorted(f"gs://{bucket}/{blob.name}" for blob in blobs if not blob.name.endswith("/"))


def _move_objects(client: storage.Client, moves: Sequence[tuple[str, str]], workers: int) -> None:
    if workers < 1:
        raise ValueError("workers must be at least one")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_move_object, client=client, source=source, destination=destination)
            for source, destination in moves
        ]
        for future in futures:
            future.result()


def _move_object(client: storage.Client, source: str, destination: str) -> None:
    source_bucket_name, source_name = _split_gcs_url(source)
    destination_bucket_name, destination_name = _split_gcs_url(destination)
    source_bucket = client.bucket(source_bucket_name)
    source_blob = source_bucket.blob(source_name)
    destination_bucket = client.bucket(destination_bucket_name)
    source_bucket.copy_blob(
        blob=source_blob, destination_bucket=destination_bucket, new_name=destination_name
    )
    source_blob.delete()


def _split_gcs_url(url: str) -> tuple[str, str]:
    """Split a ``gs://bucket/name`` URL into its bucket and object name.

    Args:
        url: A fully qualified ``gs://`` object URL.

    Returns:
        A tuple of (bucket name, object name).

    Raises:
        ValueError: If the URL is not a ``gs://`` object URL.
    """
    if not url.startswith("gs://"):
        raise ValueError(f"Not a gs:// URL: {url}")
    bucket, _, name = url.removeprefix("gs://").partition("/")
    if not name:
        raise ValueError(f"URL has no object name: {url}")
    return bucket, name


if __name__ == "__main__":
    main()
