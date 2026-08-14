#!/usr/bin/env python3
"""Copy a stratified sample of egocentric deliveries into the client's delivery format.

Take an equal number of videos from each activity category (default 10 each) from a source
pool bucket and lay them out in the directory structure the data-provider spec asks for, so
the formatting can be validated with the client before a full delivery. The category is read
off the source clip name; it is carried in a data column, never encoded in a file name.

Source layout (produced by ``sample_gcs_review.py``), per video ``{stem}``::

    gs://{source-bucket}/{source-prefix}/{stem}.mp4
    gs://{source-bucket}/{source-prefix}/{stem}_transcript.json   (or dot variants)
    gs://{source-bucket}/{source-prefix}/{stem}_metadata.json     (or dot variant)

Delivery layout written under ``gs://{dest-bucket}/{dest-root}/``::

    README.md
    {section}/{batch}/data.json             JSONL, one flat record per video
    {section}/{batch}/videos/{n}.mp4        homogeneous video attachments
    {section}/{batch}/transcripts/{n}.json  homogeneous transcript attachments

File names are numeric (``1.mp4`` / ``1.json``); a shared numeric prefix ties a video to its
transcript. No data is encoded in file or directory names, per the spec. Each ``data.json``
record is a flat JSON object: reserved columns ``relative_path`` (the video path),
``asset_id``, ``asset_type``, ``transcript_path`` (paths relative to ``data.json``) and
``name`` (the descriptive clip name with the category prefix stripped), plus every field from
the vendor metadata file with sanitized column names. Nested metadata values are serialized to
a JSON string so records stay flat, as the spec requires. All records in a batch share the
same schema; fields missing from a given video are filled with ``null``.

Videos and transcripts are copied server-side (no local download). Only the small metadata
JSON files are read, to build the records. The command is a dry run unless ``--apply`` is
given; run with the ``cloud-storage`` extra installed.

Examples:
    uv run --extra cloud-storage python scripts/build_delivery_sample.py
    uv run --extra cloud-storage python scripts/build_delivery_sample.py --apply --replace
"""

# Reuse the sampler's private GCS helpers so triplet grouping stays single-sourced.
# ruff: noqa: SLF001
from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import tempfile
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
# The five activity categories to sample from; a clip's category is the prefix of its name.
DEFAULT_CATEGORIES = (
    "General",
    "Hobbies_and_Arts",
    "Home_Daily_Tasks",
    "Personal_Care",
    "Repairs_and_DIY",
)
DEFAULT_PER_CATEGORY = 10
DEFAULT_SEED = 42
DEFAULT_WORKERS = 8

VIDEOS_DIR = "videos"
TRANSCRIPTS_DIR = "transcripts"
DATA_FILE = "data.json"
README_FILE = "README.md"

ASSET_TYPE_VIDEO = "VIDEO"
# Reserved columns lead every record; ``relative_path`` is the spec's always-required link.
RESERVED_COLUMNS = ("relative_path", "asset_id", "asset_type", "transcript_path", "name")
_COLUMN_DESCRIPTIONS = {
    "relative_path": "Path of the video file relative to this data file.",
    "asset_id": "Unique identifier for the asset.",
    "asset_type": "Asset type, always VIDEO for this dataset.",
    "transcript_path": "Path of the transcript JSON relative to this data file, or null.",
    "name": "Descriptive clip name with the category prefix removed.",
    "title": "Human-readable title of the clip.",
    "description": "Description of the activity shown in the video.",
    "publication_date": "Delivery / creation date of the clip.",
    "category": "Activity category of the clip.",
    "duration": "Video duration formatted as HH:MM:SS.",
    "duration_s": "Video duration in seconds.",
    "language": "Primary spoken language as an ISO code.",
    "resolution": "Video resolution as WIDTHxHEIGHT.",
    "wpm": "Narration speech rate in words per minute.",
}
_ALWAYS_REQUIRED_COLUMNS = {"relative_path", "asset_id", "asset_type"}
_BYTES_PER_UNIT = 1024
# Header bytes fetched per video so ffprobe can read stream metadata without the full file.
_VIDEO_HEADER_BYTES = 4 * 1024 * 1024
# Chars the spec forbids in column names.
_INVALID_COLUMN_CHARS = re.compile(r"[^0-9a-z._-]+")


@dataclass(frozen=True)
class DeliveryItem:
    """A source video mapped to its destination number and flat record.

    Attributes:
        number: 1-based sequence number; the numeric base name of the destination files.
        stem: Source stem (relative path under the source prefix, no extension).
        category: Activity category the clip was sampled under.
        display_name: Descriptive clip name with the category prefix removed.
        video_url: Source ``gs://`` URL of the video.
        transcript_url: Source ``gs://`` URL of the transcript, or ``None``.
        record: Flat JSON record written to ``data.json`` for this video.
    """

    number: int
    stem: str
    category: str
    display_name: str
    video_url: str
    transcript_url: str | None
    record: dict[str, Any]


@dataclass(frozen=True)
class DeliveryStats:
    """Aggregate stats over the selected deliveries, for the README.

    Attributes:
        video_count: Number of videos.
        transcript_count: Number of videos that ship with a transcript.
        video_bytes: Total size of the video files in bytes.
        transcript_bytes: Total size of the transcript files in bytes.
        total_duration_s: Sum of per-video durations in seconds, when known.
        total_frames: Sum of per-video frame counts, when every video was probed.
    """

    video_count: int
    transcript_count: int
    video_bytes: int
    transcript_bytes: int
    total_duration_s: float | None
    total_frames: int | None


def main() -> None:
    """Build and (optionally) write the delivery sample per command-line arguments."""
    args = _parse_args()
    client = sampler._storage_client(project=args.project)

    items = build_items(
        client=client,
        source_bucket=args.source_bucket,
        source_prefix=args.source_prefix,
        categories=tuple(args.categories),
        per_category=args.per_category,
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

    if args.replace:
        deleted = _delete_prefix(client=client, bucket=args.dest_bucket, prefix=f"{batch_root}/")
        print(f"Replaced batch: deleted {deleted} existing object(s) under {batch_root}/.")
    _copy_assets(
        client=client,
        items=items,
        dest_bucket=args.dest_bucket,
        batch_root=batch_root,
        workers=args.workers,
    )
    stats = gather_stats(client=client, items=items, probe_frames=args.probe_frames)
    data_jsonl = "".join(json.dumps(record) + "\n" for record in records)
    _upload_text(client=client, url=data_url, text=data_jsonl, content_type="application/json")
    _upload_text(
        client=client,
        url=readme_url,
        text=render_readme(records=records, stats=stats, section=args.section, batch=args.batch),
        content_type="text/markdown",
    )
    print(
        f"\nWrote {len(items)} video(s), {DATA_FILE}, and {README_FILE} to gs://{args.dest_bucket}/."
    )


def build_items(  # noqa: PLR0913  parameters mirror the discovery + sampling knobs.
    client: storage.Client,
    source_bucket: str,
    source_prefix: str,
    categories: tuple[str, ...],
    per_category: int,
    seed: int,
    require_transcript: bool,
) -> list[DeliveryItem]:
    """Discover complete deliveries, sample ``per_category`` per category, and build records.

    Args:
        client: Authenticated storage client.
        source_bucket: Bucket holding the source deliveries.
        source_prefix: Prefix within the source bucket to read, e.g. ``pool``.
        categories: Activity categories to sample from; a clip's category prefixes its name.
        per_category: Number of videos to sample from each category.
        seed: Random seed for reproducible sampling.
        require_transcript: Keep only deliveries that also have a transcript.

    Returns:
        The chosen deliveries with numeric names and flat records, grouped by category order.
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
    chosen = _select_stratified(
        groups=eligible, categories=categories, per_category=per_category, seed=seed
    )

    items: list[DeliveryItem] = []
    for number, (group, category, display_name) in enumerate(chosen, start=1):
        video_url = _first_with_suffix(group.files, (sampler.VIDEO_SUFFIX,))
        transcript_url = _first_with_suffix_or_none(group.files, sampler.TRANSCRIPT_SUFFIXES)
        metadata_url = _first_with_suffix_or_none(group.files, sampler.METADATA_SUFFIXES)
        metadata = _read_metadata(client=client, url=metadata_url) if metadata_url else {}
        items.append(
            DeliveryItem(
                number=number,
                stem=group.stem,
                category=category,
                display_name=display_name,
                video_url=video_url,
                transcript_url=transcript_url,
                record=_build_record(
                    number=number,
                    display_name=display_name,
                    metadata=metadata,
                    has_transcript=transcript_url is not None,
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
    records: Sequence[Mapping[str, Any]],
    stats: DeliveryStats,
    section: str,
    batch: str,
) -> str:
    """Render a README describing the delivery, its schema, and how files link together."""
    columns = list(records[0].keys()) if records else list(RESERVED_COLUMNS)
    return (
        "# Egocentric Video Dataset\n\n"
        "## Data provider overview\n"
        "Lightly AI. Egocentric (first-person) videos of everyday tasks, collected via Toloka\n"
        "and quality-checked by Lightly's automated QA pipeline.\n\n"
        "## Dataset overview\n"
        "Multimodal: each record is one egocentric video with a spoken-narration transcript and\n"
        "per-video metadata. Videos are sampled evenly across activity categories (see the\n"
        "`category` column). The video and transcript are linked from the structured data file\n"
        f"by relative path (`relative_path`, `transcript_path`) in "
        f"`{section}/{batch}/data.json`.\n\n"
        "## Basic dataset stats\n"
        f"{_render_stats(stats)}\n\n"
        "## Restrictions\n"
        "- Usage restrictions: TODO confirm with provider.\n"
        "- PII / child-related data: TODO confirm with provider.\n\n"
        "## Data collection method\n"
        "Sourced from creator-recorded egocentric video via Toloka. Creation date is included per\n"
        "record in the `publication_date` column.\n\n"
        "## Formats\n"
        "- Video: MP4 (H.264), 1080p or higher.\n"
        "- Transcript: JSON (faster-whisper output with segment- and word-level timestamps).\n"
        "- Structured records: JSONL (`data.json`), one flat record per video.\n\n"
        "## Schema\n"
        f"{_render_schema_table(records=records, columns=columns)}\n\n"
        "Remaining columns mirror the vendor metadata file. Nested metadata values, if any, are\n"
        "serialized as JSON strings so every record stays flat.\n\n"
        "## Linking files\n"
        f"File names are numeric; a shared number ties a video to its transcript. Each record in\n"
        f"`{section}/{batch}/data.json` links to its media by relative path:\n"
        f"`relative_path` -> `{VIDEOS_DIR}/<asset_id>.mp4`, "
        f"`transcript_path` -> `{TRANSCRIPTS_DIR}/<asset_id>.json` (`asset_id` is the number).\n"
    )


def gather_stats(
    client: storage.Client, items: Sequence[DeliveryItem], probe_frames: bool
) -> DeliveryStats:
    """Collect aggregate stats over the delivered items for the README.

    Sizes come from object metadata (cheap HEAD requests). Frame counts, when
    ``probe_frames`` is set, come from ffprobe reading only each video's header. If any video
    cannot be probed, the total frame count is reported as unknown rather than a partial sum.

    Args:
        client: Authenticated storage client.
        items: The delivered items.
        probe_frames: Whether to probe each video's header to count frames.

    Returns:
        The aggregate stats.
    """
    video_bytes = 0
    transcript_bytes = 0
    total_duration_s = 0.0
    total_frames = 0
    duration_known = True
    frames_known = probe_frames
    for item in items:
        video_bytes += _blob_size(client=client, url=item.video_url)
        if item.transcript_url is not None:
            transcript_bytes += _blob_size(client=client, url=item.transcript_url)
        duration = item.record.get("duration_s")
        if isinstance(duration, (int, float)):
            total_duration_s += float(duration)
        else:
            duration_known = False
        if probe_frames:
            frames = _probe_video_frames(client=client, url=item.video_url)
            if frames is None:
                frames_known = False
            else:
                total_frames += frames
    return DeliveryStats(
        video_count=len(items),
        transcript_count=sum(1 for item in items if item.transcript_url is not None),
        video_bytes=video_bytes,
        transcript_bytes=transcript_bytes,
        total_duration_s=total_duration_s if duration_known else None,
        total_frames=total_frames if frames_known else None,
    )


def _render_stats(stats: DeliveryStats) -> str:
    lines = [
        "- Asset types: video (MP4) with companion transcript (JSON).",
        f"- Videos: {stats.video_count} ({stats.transcript_count} with transcripts).",
        f"- Video size: {_human_bytes(stats.video_bytes)} total.",
        f"- Transcript size: {_human_bytes(stats.transcript_bytes)} total.",
    ]
    if stats.total_frames is not None:
        lines.append(f"- Frames: {stats.total_frames} total.")
    if stats.total_duration_s is not None:
        lines.append(f"- Duration: {stats.total_duration_s / 3600:.2f} hours total.")
    return "\n".join(lines)


def _render_schema_table(records: Sequence[Mapping[str, Any]], columns: Sequence[str]) -> str:
    header = "| field | type | is_required | description |\n| --- | --- | --- | --- |"
    rows = [
        f"| `{column}` | {_column_type(records=records, column=column)} "
        f"| {'yes' if column in _ALWAYS_REQUIRED_COLUMNS else 'no'} "
        f"| {_COLUMN_DESCRIPTIONS.get(column, 'Vendor-provided metadata field.')} |"
        for column in columns
    ]
    return "\n".join([header, *rows])


def _column_type(records: Sequence[Mapping[str, Any]], column: str) -> str:
    for record in records:
        value = record.get(column)
        if value is not None:
            return _spec_type(value)
    return "text"


def _spec_type(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    return "text"


def _human_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < _BYTES_PER_UNIT or unit == "TB":
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= _BYTES_PER_UNIT
    return f"{value:.1f} TB"


def _blob_size(client: storage.Client, url: str) -> int:
    bucket_name, name = sampler._split_gcs_url(url)
    blob = client.bucket(bucket_name).get_blob(name)
    return blob.size if blob is not None and blob.size is not None else 0


def _probe_video_frames(client: storage.Client, url: str) -> int | None:
    """Return the video's frame count from ffprobe reading only its header, or None on failure.

    Downloads a small header slice (enough for a faststart MP4's ``moov`` atom) and asks ffprobe
    for the stream's frame count, falling back to ``round(fps * duration)`` when the container
    does not store an explicit count.
    """
    bucket_name, name = sampler._split_gcs_url(url)
    blob = client.bucket(bucket_name).blob(name)
    try:
        header = blob.download_as_bytes(start=0, end=_VIDEO_HEADER_BYTES - 1)
    except Exception:  # Probing is best-effort; any download error means unknown.
        return None
    with tempfile.NamedTemporaryFile(suffix=".mp4") as handle:
        handle.write(header)
        handle.flush()
        return _ffprobe_frames(path=handle.name)


def _ffprobe_frames(path: str) -> int | None:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=nb_frames,avg_frame_rate,duration",
        "-of",
        "json",
        path,
    ]
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=True)
        streams = json.loads(completed.stdout).get("streams", [])
    except (subprocess.SubprocessError, json.JSONDecodeError, OSError):
        return None
    if not streams:
        return None
    return _frames_from_stream(stream=streams[0])


def _frames_from_stream(stream: Mapping[str, Any]) -> int | None:
    nb_frames = stream.get("nb_frames")
    if isinstance(nb_frames, str) and nb_frames.isdigit():
        return int(nb_frames)
    fps = _parse_frame_rate(stream.get("avg_frame_rate"))
    duration = stream.get("duration")
    if fps is not None and isinstance(duration, str):
        try:
            return round(fps * float(duration))
        except ValueError:
            return None
    return None


def _parse_frame_rate(value: Any) -> float | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    numerator, denominator = value.split("/", 1)
    try:
        denominator_value = float(denominator)
        return float(numerator) / denominator_value if denominator_value else None
    except ValueError:
        return None


def _select_stratified(
    groups: Sequence[Any],
    categories: tuple[str, ...],
    per_category: int,
    seed: int,
) -> list[tuple[Any, str, str]]:
    """Sample ``per_category`` groups from each category, in category then stem order.

    A group's category is the leading segment of its clip name; groups whose name matches
    none of ``categories`` are skipped. When a category has fewer than ``per_category``
    eligible videos, all of them are taken and a warning is printed.

    Returns:
        ``(group, category, display_name)`` triples, ordered by ``categories`` then stem.
    """
    if per_category < 1:
        raise ValueError("per_category must be at least one")
    buckets: dict[str, list[tuple[Any, str]]] = {category: [] for category in categories}
    for group in groups:
        match = _category_of(stem=group.stem, categories=categories)
        if match is not None:
            category, display_name = match
            buckets[category].append((group, display_name))

    rng = random.Random(seed)
    chosen: list[tuple[Any, str, str]] = []
    for category in categories:
        members = sorted(buckets[category], key=lambda pair: pair[0].stem)
        if len(members) <= per_category:
            if len(members) < per_category:
                print(
                    f"Warning: category {category!r} has only {len(members)} eligible "
                    f"video(s), fewer than the requested {per_category}."
                )
            picked = members
        else:
            picked = sorted(rng.sample(members, k=per_category), key=lambda pair: pair[0].stem)
        chosen.extend((group, category, display_name) for group, display_name in picked)
    return chosen


def _category_of(stem: str, categories: tuple[str, ...]) -> tuple[str, str] | None:
    """Return the ``(category, display_name)`` for a stem, or None if it matches no category.

    The category is the longest matching prefix of the clip name (the stem's final path
    segment); the display name is that clip name with the ``{category}_`` prefix removed.
    """
    clip = stem.rsplit("/", 1)[-1]
    for category in sorted(categories, key=len, reverse=True):
        prefix = f"{category}_"
        if clip.startswith(prefix):
            return category, clip[len(prefix) :]
    return None


def _build_record(
    number: int, display_name: str, metadata: Mapping[str, Any], has_transcript: bool
) -> dict[str, Any]:
    """Build one flat record: sanitized vendor metadata plus reserved columns."""
    record: dict[str, Any] = {}
    for key, value in metadata.items():
        column = _sanitize_column(key)
        record[column] = value if _is_scalar(value) else json.dumps(value)
    record["relative_path"] = f"{VIDEOS_DIR}/{number}.mp4"
    record["asset_id"] = str(number)
    record["asset_type"] = ASSET_TYPE_VIDEO
    record["transcript_path"] = f"{TRANSCRIPTS_DIR}/{number}.json" if has_transcript else None
    record["name"] = display_name
    return record


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
            (item.video_url, f"gs://{dest_bucket}/{batch_root}/{VIDEOS_DIR}/{item.number}.mp4")
        )
        if item.transcript_url is not None:
            copies.append(
                (
                    item.transcript_url,
                    f"gs://{dest_bucket}/{batch_root}/{TRANSCRIPTS_DIR}/{item.number}.json",
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


def _delete_prefix(client: storage.Client, bucket: str, prefix: str) -> int:
    """Delete every object under ``prefix`` in ``bucket``; return how many were deleted."""
    blobs = list(client.list_blobs(client.bucket(bucket), prefix=prefix))
    for blob in blobs:
        blob.delete()
    return len(blobs)


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
    per_category: dict[str, int] = {}
    for item in items:
        per_category[item.category] = per_category.get(item.category, 0) + 1
    print(
        f"{len(items)} video(s) selected ({transcript_count} with transcripts); "
        f"{len(columns)} data.json columns."
    )
    print(f"Per category: {', '.join(f'{name}={count}' for name, count in per_category.items())}")
    print(f"Columns: {', '.join(columns)}")
    for item in items:
        print(f"{item.video_url} -> gs://{dest_bucket}/{batch_root}/{VIDEOS_DIR}/{item.number}.mp4")
        if item.transcript_url is not None:
            print(
                f"{item.transcript_url} -> "
                f"gs://{dest_bucket}/{batch_root}/{TRANSCRIPTS_DIR}/{item.number}.json"
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
    parser.add_argument(
        "--categories",
        nargs="+",
        default=list(DEFAULT_CATEGORIES),
        help="Activity categories to sample from; a clip's category prefixes its name.",
    )
    parser.add_argument(
        "--per-category",
        type=int,
        default=DEFAULT_PER_CATEGORY,
        help="Number of videos to sample from each category.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument(
        "--allow-missing-transcript",
        action="store_true",
        help="Include videos that ship without a transcript.",
    )
    parser.add_argument(
        "--probe-frames",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Count frames via ffprobe over each video's header for the README stats.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the objects. Without this flag, only print the plan.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="With --apply, delete existing objects under the batch before writing.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
