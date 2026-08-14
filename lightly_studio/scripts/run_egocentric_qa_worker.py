#!/usr/bin/env python3
"""Pull egocentric video triplets from GCS, run QA, and write per-video records.

This is the compute-side counterpart to ``sample_gcs_review.py``. The sampler
partitions ``source`` into ``review``/``pool``; this worker consumes both prefixes
across every ``-qa`` bucket, runs the QA pipeline on each complete triplet, and
writes a tiny JSON result record back to a results bucket. Original video bytes are
never copied to represent status (see the reference-record pattern).

Coordination is via per-item atomic markers in the results bucket, NOT a central
ledger, so any number of workers can run concurrently with no shared queue:

    state/{bucket}/{stem}.claimed   lease held by one worker (create-if-absent)
    state/{bucket}/{stem}.done      terminal marker; item is skipped once present
    records/{bucket}/{stem}.json    the QA result record (durable output)

A claim is won with an ``if_generation_match=0`` create (GCS returns 412 if the
object already exists), which is an atomic compare-and-swap: exactly one worker
wins the race. A ``.claimed`` older than ``--lease-seconds`` is treated as
abandoned (crashed worker) and stolen with a generation-matched overwrite.

Per-video records carry the raw signals (duration, language, static-camera bool,
per-video verdict). DATASET-level criteria (average duration, English %, static
camera %) are meaningless for a single video and must be computed by a separate
aggregation pass over all records after the run.

Run inside the ``lightly_studio`` environment (needs the QA deps and the
``cloud-storage`` extra):
    uv run --extra cloud-storage python scripts/run_egocentric_qa_worker.py \
        --results-bucket lightly-qa-results --once --max-items 20
"""

from __future__ import annotations

# This worker deliberately reuses the sampler's and pipeline's private helpers so the
# triplet definition and QA stages stay single-sourced.
# ruff: noqa: SLF001

import argparse
import json
import socket
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

# The sampler owns the shared GCS grouping/URL helpers; reuse them so the triplet
# definition stays in one place.
import sample_gcs_review as sampler

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

DEFAULT_PROJECT = sampler.DEFAULT_PROJECT
DEFAULT_BUCKET_SUFFIX = sampler.DEFAULT_BUCKET_SUFFIX
DEFAULT_WORK_PREFIXES = ("review", "pool")
DEFAULT_RESULTS_BUCKET = "lightly-qa-results"
DEFAULT_STATE_PREFIX = "state"
DEFAULT_RECORDS_PREFIX = "records"
DEFAULT_LEASE_SECONDS = 3600
DEFAULT_POLL_SECONDS = 60

CLAIMED_SUFFIX = ".claimed"
DONE_SUFFIX = ".done"


@dataclass(frozen=True)
class WorkerConfig:
    """Resolved worker settings, mostly a typed view over parsed args."""

    project: str
    buckets: tuple[str, ...]
    bucket_suffix: str
    work_prefixes: tuple[str, ...]
    results_bucket: str
    state_prefix: str
    records_prefix: str
    lease_seconds: int
    poll_seconds: int
    scratch_dir: Path
    worker_id: str
    once: bool
    max_items: int | None
    dry_run: bool
    qa: QaConfig


@dataclass(frozen=True)
class QaConfig:
    """Settings passed straight through to the QA pipeline."""

    caption_unit: str
    action_pause_s: float
    action_window_padding_s: float
    action_min_window_s: float
    action_max_words: int
    narration_llm_base_url: str
    narration_llm_provider: str
    narration_llm_model: str
    narration_llm_api_key: str | None
    classification_batch_size: int


@dataclass(frozen=True)
class WorkItem:
    """One complete triplet to process, identified by bucket + stem."""

    bucket: str
    stem: str
    files: tuple[str, ...]  # full gs:// URLs, video first

    @property
    def video_url(self) -> str:
        return self.files[0]


@dataclass
class VideoQaResult:
    """Outcome of QA for one video, serialized into a record."""

    status: str  # "pass" | "review" | "fail" | "error"
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


def main() -> None:
    """Discover, claim, and process work until drained (``--once``) or forever."""
    config = _config_from_args(_parse_args())
    client = sampler._storage_client(project=config.project)
    processed = 0
    while True:
        items = discover_work(client=client, config=config)
        print(f"{len(items)} unclaimed complete triplet(s) available.", flush=True)
        made_progress = False
        for item in items:
            if config.max_items is not None and processed >= config.max_items:
                print(f"Reached --max-items {config.max_items}; stopping.", flush=True)
                return
            if _process_item(client=client, item=item, config=config):
                processed += 1
                made_progress = True
        if config.once:
            print(f"--once: drained. Processed {processed} item(s).", flush=True)
            return
        if not made_progress:
            time.sleep(config.poll_seconds)


def discover_work(client: storage.Client, config: WorkerConfig) -> list[WorkItem]:
    """List every complete, not-yet-done triplet across buckets and work prefixes."""
    buckets = config.buckets or tuple(
        sampler._list_buckets(client=client, suffix=config.bucket_suffix)
    )
    items: list[WorkItem] = []
    for bucket in buckets:
        for prefix in config.work_prefixes:
            root = sampler._gcs_root(bucket=bucket, prefix=prefix)
            objects = sampler._list_objects(client=client, bucket=bucket, prefix=prefix)
            groups, _ = sampler.group_source_objects(objects=objects, source_root=root)
            for group in groups:
                if not group.is_complete:
                    continue  # sampler quarantines these; skip partial triplets.
                item = WorkItem(bucket=bucket, stem=group.stem, files=tuple(group.files))
                if _is_done(client=client, item=item, config=config):
                    continue
                items.append(item)
    return items


def _process_item(client: storage.Client, item: WorkItem, config: WorkerConfig) -> bool:
    """Claim, run QA, and record one item. Returns True if this worker processed it."""
    print(f"\n--- {item.bucket}/{item.stem} ---", flush=True)
    if config.dry_run:
        print("Dry run: would claim and process.", flush=True)
        return False
    if not _claim(client=client, item=item, config=config):
        print("Already claimed by another worker; skipping.", flush=True)
        return False

    scratch = Path(tempfile.mkdtemp(prefix="qa-", dir=config.scratch_dir))
    try:
        video_path, transcript_path, metadata_path = _download_triplet(
            client=client, item=item, scratch=scratch
        )
        result = _safe_run_qa(
            video_path=video_path,
            transcript_path=transcript_path,
            metadata_path=metadata_path,
            scratch=scratch,
            config=config,
        )
        _write_record(client=client, item=item, result=result, config=config)
        _mark_done(client=client, item=item, config=config)
        _release_claim(client=client, item=item, config=config)
        print(f"Recorded status={result.status}.", flush=True)
        return True
    finally:
        _rmtree(scratch)


# --- QA seam --------------------------------------------------------------------
# Everything below is the single place the real QA logic lives. The plumbing above
# does not care how QA is computed, only that it returns a VideoQaResult.


def _safe_run_qa(
    video_path: Path,
    transcript_path: Path,
    metadata_path: Path,
    scratch: Path,
    config: WorkerConfig,
) -> VideoQaResult:
    """Run QA, turning any failure into an ``error`` record so the loop continues."""
    try:
        return run_video_qa(
            video_path=video_path,
            transcript_path=transcript_path,
            metadata_path=metadata_path,
            scratch=scratch,
            config=config,
        )
    except Exception as error:  # One poison video must not stop the batch.
        traceback.print_exc()
        return VideoQaResult(status="error", error=f"{type(error).__name__}: {error}")


def run_video_qa(
    video_path: Path,
    transcript_path: Path,
    metadata_path: Path,  # noqa: ARG001  vendor metadata cross-check is TODO.
    scratch: Path,
    config: WorkerConfig,
) -> VideoQaResult:
    """Run the per-video QA stages on a throwaway SQLite DB and extract the verdict.

    Reuses the pipeline stages that do not depend on PE embeddings or faster-whisper
    (transcripts ship in the triplet). Dataset-level criteria are intentionally NOT
    evaluated here; only per-video signals are captured for later aggregation.

    NOTE: this assumes the shipped ``{stem}_transcript.json`` is faster-whisper JSON
    that ``whisper_transcript.load_whisper_transcript`` can parse directly. If the
    vendor format differs, convert it into that shape here (the only adapter seam).
    """
    # Imported lazily so the sampler helpers and this module stay importable without
    # the heavy QA dependency tree (useful for unit-testing the plumbing).
    import run_egocentric_qa as pipeline  # noqa: PLC0415
    from lightly_studio.core.video.video_dataset import VideoDataset  # noqa: PLC0415
    from lightly_studio.database import db_manager  # noqa: PLC0415
    from lightly_studio.dataset.whisper_transcript import ActionPhraseSettings  # noqa: PLC0415
    from lightly_studio.resolvers import metadata_resolver  # noqa: PLC0415

    db_manager.connect(db_file=scratch / "qa.db", cleanup_existing=True)
    dataset = VideoDataset.create(name="egocentric-qa-worker")
    dataset.add_videos_from_path(path=video_path.parent, embed=False, embed_frames=False)

    dataset.compute_quality_scores()
    pipeline._write_technical_qa_metadata(dataset=dataset)

    captions_by_video = pipeline._create_transcript_captions(
        dataset=dataset,
        transcript_paths={video_path.resolve(): transcript_path},
        caption_unit=config.qa.caption_unit,
        action_phrase_settings=ActionPhraseSettings(
            pause_threshold_s=config.qa.action_pause_s,
            window_padding_s=config.qa.action_window_padding_s,
            min_window_duration_s=config.qa.action_min_window_s,
            max_words=config.qa.action_max_words,
        ),
    )
    classifier = pipeline._create_narration_classifier(args=_qa_args_namespace(config=config))
    pipeline._classify_narration_captions(
        dataset=dataset,
        captions_by_video=captions_by_video,
        classifier=classifier,
        force=False,
    )
    for video, _ in captions_by_video:
        pipeline._write_qa_summary(video=video, include_legacy_caption_threshold=False)

    video = next(iter(dataset))
    row = metadata_resolver.get_by_sample_id(session=dataset.session, sample_id=video.sample_id)
    metadata = dict(row.data) if row is not None else {}
    status = metadata.get("automated_qa_status")
    return VideoQaResult(
        status=status if isinstance(status, str) else "error",
        metadata=metadata,
    )


def _qa_args_namespace(config: WorkerConfig) -> argparse.Namespace:
    """Build the arg subset the narration classifier factory reads."""
    return argparse.Namespace(
        narration_llm_base_url=config.qa.narration_llm_base_url,
        narration_llm_provider=config.qa.narration_llm_provider,
        narration_llm_model=config.qa.narration_llm_model,
        narration_llm_api_key=config.qa.narration_llm_api_key,
        classification_batch_size=config.qa.classification_batch_size,
    )


# --- GCS coordination ------------------------------------------------------------


def _state_url(item: WorkItem, suffix: str, config: WorkerConfig) -> str:
    return (
        f"gs://{config.results_bucket}/{config.state_prefix}/"
        f"{item.bucket}/{item.stem}{suffix}"
    )


def _record_url(item: WorkItem, config: WorkerConfig) -> str:
    return (
        f"gs://{config.results_bucket}/{config.records_prefix}/{item.bucket}/{item.stem}.json"
    )


def _is_done(client: storage.Client, item: WorkItem, config: WorkerConfig) -> bool:
    return _blob(client=client, url=_state_url(item, DONE_SUFFIX, config)).exists()


def _claim(client: storage.Client, item: WorkItem, config: WorkerConfig) -> bool:
    """Win the claim atomically, or steal it if the existing lease is stale."""
    from google.api_core.exceptions import PreconditionFailed  # noqa: PLC0415

    blob = _blob(client=client, url=_state_url(item, CLAIMED_SUFFIX, config))
    payload = json.dumps({"worker_id": config.worker_id, "claimed_at": _now_iso()})
    try:
        blob.upload_from_string(payload, if_generation_match=0)
        return True
    except PreconditionFailed:
        return _steal_if_stale(blob=blob, payload=payload, config=config)


def _steal_if_stale(blob: storage.Blob, payload: str, config: WorkerConfig) -> bool:
    from google.api_core.exceptions import PreconditionFailed  # noqa: PLC0415

    blob.reload()
    claimed_at = _parse_claimed_at(blob=blob)
    age_s = (datetime.now(tz=timezone.utc) - claimed_at).total_seconds() if claimed_at else None
    if age_s is None or age_s < config.lease_seconds:
        return False
    print(f"Stealing stale claim (age {age_s:.0f}s > lease {config.lease_seconds}s).", flush=True)
    try:
        blob.upload_from_string(payload, if_generation_match=blob.generation)
        return True
    except PreconditionFailed:
        return False  # Another worker stole it first.


def _parse_claimed_at(blob: storage.Blob) -> datetime | None:
    try:
        claimed_at = json.loads(blob.download_as_text()).get("claimed_at")
        return datetime.fromisoformat(claimed_at) if claimed_at else None
    except (ValueError, KeyError):
        return None


def _mark_done(client: storage.Client, item: WorkItem, config: WorkerConfig) -> None:
    blob = _blob(client=client, url=_state_url(item, DONE_SUFFIX, config))
    blob.upload_from_string(json.dumps({"finished_at": _now_iso(), "worker": config.worker_id}))


def _release_claim(client: storage.Client, item: WorkItem, config: WorkerConfig) -> None:
    blob = _blob(client=client, url=_state_url(item, CLAIMED_SUFFIX, config))
    if blob.exists():
        blob.delete()


def _write_record(
    client: storage.Client, item: WorkItem, result: VideoQaResult, config: WorkerConfig
) -> None:
    record = {
        "source_uri": item.video_url,
        "bucket": item.bucket,
        "stem": item.stem,
        "worker_id": config.worker_id,
        "finished_at": _now_iso(),
        "status": result.status,
        "error": result.error,
        "metadata": result.metadata,
    }
    blob = _blob(client=client, url=_record_url(item, config))
    blob.upload_from_string(
        json.dumps(record, default=str, indent=2), content_type="application/json"
    )


def _download_triplet(
    client: storage.Client, item: WorkItem, scratch: Path
) -> tuple[Path, Path, Path]:
    """Download the triplet into ``scratch/videos`` and return the local paths.

    The companion files are identified by suffix rather than by rebuilding the name,
    so both underscore- and dot-separated conventions resolve to the right local file.
    """
    videos_dir = scratch / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    local_by_url: dict[str, Path] = {}
    for url in item.files:
        _, name = sampler._split_gcs_url(url)
        destination = videos_dir / Path(name).name
        _blob(client=client, url=url).download_to_filename(str(destination))
        local_by_url[url] = destination
    video = local_by_url[item.video_url]
    transcript = _find_companion(local_by_url=local_by_url, suffixes=sampler.TRANSCRIPT_SUFFIXES)
    metadata = _find_companion(local_by_url=local_by_url, suffixes=sampler.METADATA_SUFFIXES)
    return video, transcript, metadata


def _find_companion(local_by_url: dict[str, Path], suffixes: tuple[str, ...]) -> Path:
    """Return the one downloaded file whose name ends with any of ``suffixes``."""
    for path in local_by_url.values():
        if path.name.endswith(suffixes):
            return path
    raise FileNotFoundError(f"No downloaded companion ending in {suffixes}.")


def _blob(client: storage.Client, url: str) -> storage.Blob:
    bucket_name, name = sampler._split_gcs_url(url)
    return client.bucket(bucket_name).blob(name)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _rmtree(path: Path) -> None:
    import shutil  # noqa: PLC0415

    shutil.rmtree(path, ignore_errors=True)


# --- CLI -------------------------------------------------------------------------


def _config_from_args(args: argparse.Namespace) -> WorkerConfig:
    return WorkerConfig(
        project=args.project,
        buckets=tuple(args.bucket or ()),
        bucket_suffix=args.bucket_suffix,
        work_prefixes=tuple(args.work_prefix),
        results_bucket=args.results_bucket,
        state_prefix=args.state_prefix,
        records_prefix=args.records_prefix,
        lease_seconds=args.lease_seconds,
        poll_seconds=args.poll_seconds,
        scratch_dir=args.scratch_dir,
        worker_id=args.worker_id,
        once=args.once,
        max_items=args.max_items,
        dry_run=args.dry_run,
        qa=QaConfig(
            caption_unit=args.caption_unit,
            action_pause_s=args.action_pause_s,
            action_window_padding_s=args.action_window_padding_s,
            action_min_window_s=args.action_min_window_s,
            action_max_words=args.action_max_words,
            narration_llm_base_url=args.narration_llm_base_url,
            narration_llm_provider=args.narration_llm_provider,
            narration_llm_model=args.narration_llm_model,
            narration_llm_api_key=args.narration_llm_api_key,
            classification_batch_size=args.classification_batch_size,
        ),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument(
        "--bucket", action="append", help="Bucket to process. Repeatable. Defaults to discovery."
    )
    parser.add_argument("--bucket-suffix", default=DEFAULT_BUCKET_SUFFIX)
    parser.add_argument(
        "--work-prefix",
        action="append",
        default=None,
        help=f"Source prefix(es) to pull from. Defaults to {DEFAULT_WORK_PREFIXES}.",
    )
    parser.add_argument("--results-bucket", default=DEFAULT_RESULTS_BUCKET)
    parser.add_argument("--state-prefix", default=DEFAULT_STATE_PREFIX)
    parser.add_argument("--records-prefix", default=DEFAULT_RECORDS_PREFIX)
    parser.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)
    parser.add_argument("--poll-seconds", type=int, default=DEFAULT_POLL_SECONDS)
    parser.add_argument("--scratch-dir", type=Path, default=Path(tempfile.gettempdir()))
    parser.add_argument("--worker-id", default=f"{socket.gethostname()}-{time.time_ns()}")
    parser.add_argument(
        "--once", action="store_true", help="Drain available work then exit (no polling)."
    )
    parser.add_argument("--max-items", type=int, help="Process at most N items then exit.")
    parser.add_argument(
        "--dry-run", action="store_true", help="List claimable work without claiming or processing."
    )
    # QA pass-through (mirrors run_egocentric_qa defaults).
    parser.add_argument("--caption-unit", default="narration_chunk")
    parser.add_argument("--action-pause-s", type=float, default=0.8)
    parser.add_argument("--action-window-padding-s", type=float, default=1.0)
    parser.add_argument("--action-min-window-s", type=float, default=2.5)
    parser.add_argument("--action-max-words", type=int, default=12)
    parser.add_argument("--narration-llm-base-url", default="http://localhost:11434")
    parser.add_argument("--narration-llm-provider", choices=("ollama", "openai"), default="ollama")
    parser.add_argument("--narration-llm-model", default="qwen3:4b")
    parser.add_argument("--narration-llm-api-key", default=None)
    parser.add_argument("--classification-batch-size", type=int, default=16)
    args = parser.parse_args()
    if args.work_prefix is None:
        args.work_prefix = list(DEFAULT_WORK_PREFIXES)
    return args


if __name__ == "__main__":
    main()
