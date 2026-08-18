"""Command-line entry point for automatic QA."""

from __future__ import annotations

import argparse
import contextlib
import tempfile
import time
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import TYPE_CHECKING, TypeVar

from auto_qa import results, screen, storage, transcribe
from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager

if TYPE_CHECKING:
    from google.cloud import storage as gcs  # type: ignore[import-untyped]

_T = TypeVar("_T")
DEFAULT_DOWNLOAD_WORKERS = 4


def main(argv: Sequence[str] | None = None) -> int:
    """Run automatic QA and return a process exit code."""
    args = _parse_args(argv)
    client = storage.create_client(project=args.project)
    remote = storage.discover(
        client=client,
        buckets=tuple(args.bucket or ()),
        bucket_suffix=args.bucket_suffix,
        prefixes=tuple(args.prefix or storage.DEFAULT_WORK_PREFIXES),
    )
    if args.apply and not args.force:
        remote = results.unpublished(client=client, deliveries=remote, prefix=args.results_prefix)
    if args.max_videos is not None:
        remote = remote[: args.max_videos]
    if args.dry_run:
        _print_manifest(remote)
        return 0
    if not remote:
        print("No deliveries to process.")
        return 0

    db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=False)
    dataset = VideoDataset.load_or_create(name=args.dataset_name)
    failed = 0
    for bucket, bucket_deliveries in _by_bucket(remote).items():
        print(f"Processing gs://{bucket}/")
        batches = _chunks(bucket_deliveries, args.batch_size)
        for number, batch in enumerate(batches, start=1):
            succeeded = _process_batch(
                args=args,
                client=client,
                dataset=dataset,
                remote=batch,
                number=number,
            )
            if not succeeded:
                failed += 1
    screen.write_dataset_summary(dataset)
    if failed:
        print(f"{failed} batch(es) failed.")
        return 1
    return 0


def _process_batch(
    args: argparse.Namespace,
    client: gcs.Client,
    dataset: VideoDataset,
    remote: list[storage.RemoteDelivery],
    number: int,
) -> bool:
    print(f"Processing batch {number} ({len(remote)} delivery(ies))...", flush=True)
    try:
        with _timed_phase("Download"):
            local = storage.download(
                client=client,
                deliveries=remote,
                destination=args.destination,
                workers=args.download_workers,
            )
        if args.transcribe_missing:
            with _timed_phase("Transcription"):
                local = transcribe.missing_transcripts(
                    deliveries=local,
                    python=args.whisper_python,
                    model=args.whisper_model,
                    device=args.whisper_device,
                    compute_type=args.whisper_compute_type,
                )
        with _timed_phase("Screening"):
            screened_batch = screen.deliveries(
                dataset=dataset,
                local_deliveries=local,
                force=args.force,
            )
        uploaded = []
        if args.apply:
            with _timed_phase("Result building"):
                records = results.build(
                    dataset=dataset,
                    deliveries=local,
                    screened_batch=screened_batch,
                    prefix=args.results_prefix,
                )
            with _timed_phase("Result upload"):
                uploaded = results.upload(client=client, records=records)
    except Exception as error:
        print(f"Batch {number} failed: {error}")
        return False

    for result in screened_batch.results:
        print(f"  [{result.status}] {result.file_name}: {result.issues or 'no issues'}")
    for url in uploaded:
        print(f"  Uploaded {url}")
    if args.cleanup_local_files:
        deleted = storage.cleanup(deliveries=local, destination=args.destination)
        print(f"  Cleaned up {deleted} local file(s).")
    return True


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run automatic QA on GCS video deliveries.")
    parser.add_argument("--project", default=storage.DEFAULT_PROJECT)
    parser.add_argument("--bucket", action="append", help="Bucket to scan; repeatable.")
    parser.add_argument("--bucket-suffix", default=storage.DEFAULT_BUCKET_SUFFIX)
    parser.add_argument("--prefix", action="append", help="GCS prefix to scan; repeatable.")
    parser.add_argument("--destination", type=Path, default=Path(tempfile.gettempdir()) / "qa-pull")
    parser.add_argument(
        "--db-file", type=Path, default=Path(tempfile.gettempdir()) / "qa-screen.db"
    )
    parser.add_argument("--dataset-name", default="egocentric-qa")
    parser.add_argument("--results-prefix", default=results.DEFAULT_PREFIX)
    parser.add_argument("--batch-size", type=_positive_int, default=16)
    parser.add_argument(
        "--download-workers",
        type=_positive_int,
        default=DEFAULT_DOWNLOAD_WORKERS,
        help="Maximum number of deliveries downloaded concurrently.",
    )
    parser.add_argument("--max-videos", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--apply", action="store_true", help="Upload result JSON files.")
    parser.add_argument("--force", action="store_true", help="Rescreen existing deliveries.")
    parser.add_argument("--cleanup-local-files", action="store_true")
    parser.add_argument(
        "--transcribe-missing",
        action="store_true",
        help="Generate transcripts for deliveries that do not include one (off by default).",
    )
    parser.add_argument("--whisper-python", type=Path, default=transcribe.DEFAULT_PYTHON)
    parser.add_argument("--whisper-model", default=transcribe.DEFAULT_MODEL)
    parser.add_argument("--whisper-device", default=transcribe.DEFAULT_DEVICE)
    parser.add_argument("--whisper-compute-type", default=transcribe.DEFAULT_COMPUTE_TYPE)
    return parser.parse_args(argv)


def _chunks(items: list[_T], size: int) -> list[list[_T]]:
    return [items[start : start + size] for start in range(0, len(items), size)]


def _by_bucket(
    deliveries: list[storage.RemoteDelivery],
) -> dict[str, list[storage.RemoteDelivery]]:
    grouped: dict[str, list[storage.RemoteDelivery]] = {}
    for delivery in deliveries:
        grouped.setdefault(delivery.bucket, []).append(delivery)
    return grouped


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("must be at least 1")
    return parsed


@contextlib.contextmanager
def _timed_phase(name: str) -> Iterator[None]:
    print(f"  {name} started.", flush=True)
    started = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = time.perf_counter() - started
        print(f"  {name} failed after {elapsed:.1f}s.", flush=True)
        raise
    elapsed = time.perf_counter() - started
    print(f"  {name} finished in {elapsed:.1f}s.", flush=True)


def _print_manifest(deliveries: list[storage.RemoteDelivery]) -> None:
    print(f"Would process {len(deliveries)} delivery(ies):")
    for delivery in deliveries:
        print(f"  {delivery.bucket}/{delivery.prefix}/{delivery.stem}")
