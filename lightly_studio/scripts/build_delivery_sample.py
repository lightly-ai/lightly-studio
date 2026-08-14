#!/usr/bin/env python3
"""Copy a sample of egocentric deliveries into the client's delivery format.

Take a handful of videos (default 50) from a source pool bucket and lay them out in the
directory structure the data-provider spec asks for, so the formatting can be validated
with the client before a full delivery.

Source layout (produced by ``sample_gcs_review.py``), per video ``{stem}``::

    gs://{source-bucket}/{source-prefix}/{stem}.mp4
    gs://{source-bucket}/{source-prefix}/{stem}_transcript.json   (or dot variants)
    gs://{source-bucket}/{source-prefix}/{stem}_metadata.json     (or dot variant)

Delivery layout written under ``gs://{dest-bucket}/{dest-root}/``::

    README.md
    {section}/{batch}/data.json          JSONL, one flat record per video
    {section}/{batch}/videos/{name}.mp4  homogeneous video attachments
    {section}/{batch}/transcripts/{name}.json  homogeneous transcript attachments

Each ``data.json`` record is a flat JSON object: reserved columns ``id``, ``video_path``
and ``transcript_path`` (paths relative to ``data.json``), plus every field from the
vendor metadata file with sanitized column names. Nested metadata values are serialized to
a JSON string so records stay flat, as the spec requires. All records in a batch share the
same schema; fields missing from a given video are filled with ``null``.

Videos and transcripts are copied server-side (no local download). Only the small metadata
JSON files are read, to build the records. The command is a dry run unless ``--apply`` is
given; run with the ``cloud-storage`` extra installed.

Examples:
    uv run --extra cloud-storage python scripts/build_delivery_sample.py
    uv run --extra cloud-storage python scripts/build_delivery_sample.py --max-videos 100 --apply
"""

# Reuse the sampler's private GCS helpers so triplet grouping stays single-sourced.
# ruff: noqa: SLF001
from __future__ import annotations

import argparse
import json
import random
import re
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

if TYPE_CHECKING or __package__:
    from scripts import sample_gcs_review as sampler
else:
    import sample_gcs_review as sampler

DEFAULT_PROJECT = "egocentricdatahouse"
DEFAULT_SOURCE_BUCKET = "lightly-toloka-qa"
DEFAULT_SOURCE_PREFIX = "pool"
DEFAULT_DEST_BUCKET = "lightly-delivery"
DEFAULT_DEST_ROOT = "data_for_google/egocentric_video"
DEFAULT_SECTION = "full_data"
DEFAULT_BATCH = "batch_1"
DEFAULT_MAX_VIDEOS = 50
DEFAULT_SEED = 42
DEFAULT_WORKERS = 8

VIDEOS_DIR = "videos"
TRANSCRIPTS_DIR = "transcripts"
DATA_FILE = "data.json"
README_FILE = "README.md"

RESERVED_COLUMNS = ("id", "video_path", "transcript_path")
# Chars the spec forbids in object names and column names, respectively.
_INVALID_NAME_CHARS = re.compile(r"[^0-9a-zA-Z._-]+")
_INVALID_COLUMN_CHARS = re.compile(r"[^0-9a-z._-]+")


@dataclass(frozen=True)
class DeliveryItem:
    """A source video mapped to its destination names and flat record.

    Attributes:
        stem: Source stem (relative path under the source prefix, no extension).
        name: Flattened, spec-safe base name used for the destination files.
        video_url: Source ``gs://`` URL of the video.
        transcript_url: Source ``gs://`` URL of the transcript, or ``None``.
        record: Flat JSON record written to ``data.json`` for this video.
    """

    stem: str
    name: str
    video_url: str
    transcript_url: str | None
    record: dict[str, Any]


def main() -> None:
    """Build and (optionally) write the delivery sample per command-line arguments."""
    args = _parse_args()
    client = sampler._storage_client(project=args.project)

    items = build_items(
        client=client,
        source_bucket=args.source_bucket,
        source_prefix=args.source_prefix,
        max_videos=args.max_videos,
        seed=args.seed,
        require_transcript=not args.allow_missing_transcript,
    )
    if not items:
        print("No complete deliveries matched the source prefix; nothing to do.")
        return

    records = align_schema(items=items)
    batch_root = f"{args.dest_root.strip('/')}/{args.section}/{args.batch}"
    data_url = f"gs://{args.dest_bucket}/{batch_root}/{DATA_FILE}"
    readme_url = f"gs://{args.dest_bucket}/{args.dest_root.strip('/')}/{README_FILE}"

    _print_plan(
        items=items,
        records=records,
        dest_bucket=args.dest_bucket,
        batch_root=batch_root,
        data_url=data_url,
        readme_url=readme_url,
    )

    if not args.apply:
        print("\nDry run only. Re-run with --apply to write these objects.")
        return

    _copy_assets(
        client=client,
        items=items,
        dest_bucket=args.dest_bucket,
        batch_root=batch_root,
        workers=args.workers,
    )
    data_jsonl = "".join(json.dumps(record) + "\n" for record in records)
    _upload_text(client=client, url=data_url, text=data_jsonl, content_type="application/json")
    _upload_text(
        client=client,
        url=readme_url,
        text=render_readme(items=items, records=records, section=args.section, batch=args.batch),
        content_type="text/markdown",
    )
    print(
        f"\nWrote {len(items)} video(s), {DATA_FILE}, and {README_FILE} to gs://{args.dest_bucket}/."
    )


def build_items(  # noqa: PLR0913  parameters mirror the discovery + sampling knobs.
    client: storage.Client,
    source_bucket: str,
    source_prefix: str,
    max_videos: int,
    seed: int,
    require_transcript: bool,
) -> list[DeliveryItem]:
    """Discover complete deliveries, sample up to ``max_videos``, and build their records.

    Args:
        client: Authenticated storage client.
        source_bucket: Bucket holding the source deliveries.
        source_prefix: Prefix within the source bucket to read, e.g. ``pool``.
        max_videos: Maximum number of videos to include.
        seed: Random seed for reproducible sampling.
        require_transcript: Keep only deliveries that also have a transcript.

    Returns:
        The chosen deliveries with their destination names and flat records, sorted by stem.
    """
    source_root = sampler._gcs_root(bucket=source_bucket, prefix=source_prefix)
    objects = sampler._list_objects(client=client, bucket=source_bucket, prefix=source_prefix)
    groups, _ = sampler.group_source_objects(objects=objects, source_root=source_root)

    eligible = [
        group
        for group in groups
        if group.has_video
        and group.has_metadata
        and (not require_transcript or _has_transcript(group.files))
    ]
    chosen = _sample_groups(groups=eligible, max_videos=max_videos, seed=seed)

    items: list[DeliveryItem] = []
    seen_names: dict[str, str] = {}
    for group in chosen:
        name = _flatten_stem(group.stem)
        if name in seen_names:
            raise ValueError(
                f"Destination name collision: {group.stem!r} and {seen_names[name]!r} "
                f"both map to {name!r}."
            )
        seen_names[name] = group.stem
        video_url = _first_with_suffix(group.files, (sampler.VIDEO_SUFFIX,))
        transcript_url = _first_with_suffix_or_none(group.files, sampler.TRANSCRIPT_SUFFIXES)
        metadata_url = _first_with_suffix_or_none(group.files, sampler.METADATA_SUFFIXES)
        metadata = _read_metadata(client=client, url=metadata_url) if metadata_url else {}
        items.append(
            DeliveryItem(
                stem=group.stem,
                name=name,
                video_url=video_url,
                transcript_url=transcript_url,
                record=_build_record(
                    name=name, metadata=metadata, has_transcript=transcript_url is not None
                ),
            )
        )
    return items


def align_schema(items: Sequence[DeliveryItem]) -> list[dict[str, Any]]:
    """Return records sharing one schema, null-filling fields absent from a given video.

    The spec requires every structured record in a batch to have the same set of columns.
    Reserved columns lead, then vendor columns in first-seen order.
    """
    columns: list[str] = list(RESERVED_COLUMNS)
    for item in items:
        for key in item.record:
            if key not in columns:
                columns.append(key)
    return [{column: item.record.get(column) for column in columns} for item in items]


def render_readme(
    items: Sequence[DeliveryItem],
    records: Sequence[Mapping[str, Any]],
    section: str,
    batch: str,
) -> str:
    """Render a README describing the delivery, its schema, and how files link together."""
    columns = list(records[0].keys()) if records else list(RESERVED_COLUMNS)
    transcript_count = sum(1 for item in items if item.transcript_url is not None)
    column_lines = "\n".join(f"- `{column}`" for column in columns)
    return (
        "# Egocentric Video Dataset\n\n"
        "## General information\n"
        "- Provider: Lightly AI.\n"
        "- Source: egocentric video deliveries collected via Toloka, quality-checked by Lightly.\n"
        "- Usage restrictions: TODO confirm with provider.\n"
        f"- Data stats: {len(items)} videos, {transcript_count} with transcripts.\n"
        "- PII / child-related data: TODO confirm with provider.\n\n"
        "## Data types\n"
        "Multimodal: egocentric video with a spoken-narration transcript and "
        "per-video metadata.\n\n"
        "## Formats\n"
        "- Video: MP4 (H.264).\n"
        "- Transcript: JSON (faster-whisper output with segment- and word-level timestamps).\n"
        "- Structured records: JSONL (`data.json`), one flat record per video.\n\n"
        "## Schema (`data.json` columns)\n"
        f"{column_lines}\n\n"
        "Reserved columns: `id` uniquely names the video; `video_path` and `transcript_path` are\n"
        "paths relative to `data.json`. Remaining columns mirror the vendor metadata file; nested\n"
        "metadata values are serialized as JSON strings so every record stays flat.\n\n"
        "## Linking files\n"
        f"Each record in `{section}/{batch}/data.json` links to its media by relative path:\n"
        f"`video_path` -> `{VIDEOS_DIR}/<id>.mp4`, "
        f"`transcript_path` -> `{TRANSCRIPTS_DIR}/<id>.json`.\n"
    )


def _sample_groups(groups: Sequence[Any], max_videos: int, seed: int) -> list[Any]:
    """Return up to ``max_videos`` groups, reproducibly sampled and sorted by stem."""
    if max_videos < 1:
        raise ValueError("max_videos must be at least one")
    ordered = sorted(groups, key=lambda group: group.stem)
    if len(ordered) <= max_videos:
        return ordered
    sampled = random.Random(seed).sample(ordered, k=max_videos)
    return sorted(sampled, key=lambda group: group.stem)


def _build_record(name: str, metadata: Mapping[str, Any], has_transcript: bool) -> dict[str, Any]:
    """Build one flat record: sanitized vendor metadata plus reserved columns."""
    record: dict[str, Any] = {}
    for key, value in metadata.items():
        column = _sanitize_column(key)
        record[column] = value if _is_scalar(value) else json.dumps(value)
    record["id"] = name
    record["video_path"] = f"{VIDEOS_DIR}/{name}.mp4"
    record["transcript_path"] = f"{TRANSCRIPTS_DIR}/{name}.json" if has_transcript else None
    return record


def _flatten_stem(stem: str) -> str:
    """Flatten a source stem to a single spec-safe base name.

    Path separators become double underscores; any other character outside
    ``[0-9a-zA-Z._-]`` becomes a single underscore.
    """
    flattened = stem.replace("/", "__")
    return _INVALID_NAME_CHARS.sub("_", flattened)


def _sanitize_column(key: str) -> str:
    """Coerce a metadata key into a spec-safe column name (``[0-9a-z._-]``, no leading digit)."""
    column = _INVALID_COLUMN_CHARS.sub("_", key.lower())
    if not column:
        raise ValueError(f"Metadata key sanitizes to an empty column name: {key!r}.")
    if column[0].isdigit():
        column = f"_{column}"
    return column


def _has_transcript(files: Sequence[str]) -> bool:
    """Return whether any file in the group is a transcript companion."""
    return any(file.endswith(sampler.TRANSCRIPT_SUFFIXES) for file in files)


def _first_with_suffix(files: Sequence[str], suffixes: tuple[str, ...]) -> str:
    """Return the first file whose (lower-cased) name ends with any of ``suffixes``.

    Raises:
        ValueError: If no file matches.
    """
    match = _first_with_suffix_or_none(files=files, suffixes=suffixes)
    if match is None:
        raise ValueError(f"No file matching {suffixes} in {files}.")
    return match


def _first_with_suffix_or_none(files: Sequence[str], suffixes: tuple[str, ...]) -> str | None:
    """Return the first file whose (lower-cased) name ends with any of ``suffixes``, else None."""
    lowered = tuple(suffix.lower() for suffix in suffixes)
    for file in files:
        if file.lower().endswith(lowered):
            return file
    return None


def _is_scalar(value: Any) -> bool:
    return value is None or isinstance(value, (str, int, float, bool))


def _read_metadata(client: storage.Client, url: str) -> dict[str, Any]:
    """Download and parse a metadata JSON object; return an empty dict if it is not an object."""
    bucket_name, name = sampler._split_gcs_url(url)
    text = client.bucket(bucket_name).blob(name).download_as_text()
    parsed = json.loads(text)
    return parsed if isinstance(parsed, dict) else {}


def _copy_assets(
    client: storage.Client,
    items: Sequence[DeliveryItem],
    dest_bucket: str,
    batch_root: str,
    workers: int,
) -> None:
    """Copy every video and transcript to the delivery layout, server-side and in parallel."""
    copies: list[tuple[str, str]] = []
    for item in items:
        copies.append(
            (item.video_url, f"gs://{dest_bucket}/{batch_root}/{VIDEOS_DIR}/{item.name}.mp4")
        )
        if item.transcript_url is not None:
            copies.append(
                (
                    item.transcript_url,
                    f"gs://{dest_bucket}/{batch_root}/{TRANSCRIPTS_DIR}/{item.name}.json",
                )
            )
    if workers < 1:
        raise ValueError("workers must be at least one")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(_copy_blob, client=client, source=source, destination=destination)
            for source, destination in copies
        ]
        for future in futures:
            future.result()


def _copy_blob(client: storage.Client, source: str, destination: str) -> None:
    source_bucket_name, source_name = sampler._split_gcs_url(source)
    destination_bucket_name, destination_name = sampler._split_gcs_url(destination)
    source_bucket = client.bucket(source_bucket_name)
    source_bucket.copy_blob(
        blob=source_bucket.blob(source_name),
        destination_bucket=client.bucket(destination_bucket_name),
        new_name=destination_name,
    )


def _upload_text(client: storage.Client, url: str, text: str, content_type: str) -> None:
    bucket_name, name = sampler._split_gcs_url(url)
    client.bucket(bucket_name).blob(name).upload_from_string(text, content_type=content_type)


def _print_plan(  # noqa: PLR0913  a plan print needs every destination it will write.
    items: Sequence[DeliveryItem],
    records: Sequence[Mapping[str, Any]],
    dest_bucket: str,
    batch_root: str,
    data_url: str,
    readme_url: str,
) -> None:
    transcript_count = sum(1 for item in items if item.transcript_url is not None)
    columns = list(records[0].keys()) if records else []
    print(
        f"{len(items)} video(s) selected ({transcript_count} with transcripts); "
        f"{len(columns)} data.json columns."
    )
    print(f"Columns: {', '.join(columns)}")
    for item in items:
        print(f"{item.video_url} -> gs://{dest_bucket}/{batch_root}/{VIDEOS_DIR}/{item.name}.mp4")
        if item.transcript_url is not None:
            print(
                f"{item.transcript_url} -> "
                f"gs://{dest_bucket}/{batch_root}/{TRANSCRIPTS_DIR}/{item.name}.json"
            )
    print(f"write -> {data_url}")
    print(f"write -> {readme_url}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--source-bucket", default=DEFAULT_SOURCE_BUCKET)
    parser.add_argument("--source-prefix", default=DEFAULT_SOURCE_PREFIX)
    parser.add_argument("--dest-bucket", default=DEFAULT_DEST_BUCKET)
    parser.add_argument("--dest-root", default=DEFAULT_DEST_ROOT)
    parser.add_argument("--section", default=DEFAULT_SECTION, help="e.g. full_data or sample")
    parser.add_argument("--batch", default=DEFAULT_BATCH)
    parser.add_argument("--max-videos", type=int, default=DEFAULT_MAX_VIDEOS)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--allow-missing-transcript",
        action="store_true",
        help="Include videos that ship without a transcript.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the objects. Without this flag, only print the plan.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
