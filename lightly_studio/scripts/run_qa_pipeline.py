#!/usr/bin/env python3
"""Main QA orchestration for egocentric deliveries.

Discovers every video-bearing delivery, then downloads, transcribes, screens, and
optionally cleans it up in bounded batches. A batch is deleted only after every
file-dependent QA result has been committed to the persistent database and any
requested result uploads have succeeded.

Discover only, without downloading::

    uv run --extra cloud-storage python scripts/run_qa_pipeline.py --dry-run

Pull three deliveries to a scratch folder, transcribing any that lack a transcript::

    uv run --extra cloud-storage python scripts/run_qa_pipeline.py \
        --destination /tmp/qa-pull --max-videos 3

Delete scratch files after each successful batch::

    uv run --extra cloud-storage python scripts/run_qa_pipeline.py \
        --cleanup-local-files --apply --db-file /mnt/persistent/qa-screen.db

Pull without generating transcripts (screening fails if any are missing)::

    uv run --extra cloud-storage python scripts/run_qa_pipeline.py --no-transcribe
"""

# Reuse the sampler's private storage-client helper.
# ruff: noqa: SLF001
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from google.cloud import storage  # type: ignore[import-untyped]

    from lightly_studio.dataset import narration_classification

if TYPE_CHECKING or __package__:
    from scripts import qa_pull, qa_results, qa_screen, qa_transcribe
    from scripts import run_egocentric_qa as qa
    from scripts import sample_gcs_review as sampler
else:
    import qa_pull
    import qa_results
    import qa_screen
    import qa_transcribe
    import run_egocentric_qa as qa
    import sample_gcs_review as sampler

from lightly_studio.core.video.video_dataset import VideoDataset
from lightly_studio.database import db_manager


def main() -> None:
    """Run the bounded QA pipeline."""
    args = _parse_args()
    client = sampler._storage_client(project=args.project)
    triplets = qa_pull.discover_triplets(
        client=client,
        buckets=tuple(args.bucket or ()),
        bucket_suffix=args.bucket_suffix,
        work_prefixes=tuple(args.work_prefix),
    )
    discovered_count = len(triplets)
    if args.apply and not args.force_classify:
        triplets = qa_results.filter_unpublished_triplets(
            client=client,
            triplets=triplets,
            results_prefix=args.results_prefix,
        )
        skipped_count = discovered_count - len(triplets)
        print(f"Skipped {skipped_count} delivery(ies) with existing result records.")
    if args.max_videos is not None:
        triplets = triplets[: args.max_videos]

    if args.dry_run:
        print(f"Would pull {len(triplets)} delivery(ies):")
        for triplet in triplets:
            print(f"  {triplet.bucket}/{triplet.prefix} :: {triplet.stem}")
        return

    if triplets and not args.apply:
        print("Result upload disabled; pass --apply to write same-bucket JSON records.")

    qa_screen._chunks(triplets, args.batch_size)
    db_manager.connect(db_file=args.db_file.resolve(), cleanup_existing=False)
    dataset = VideoDataset.load_or_create(name=args.dataset_name)
    classifier = qa_screen.build_classifier(
        base_url=args.narration_llm_base_url,
        model=args.narration_llm_model,
        provider=args.narration_llm_provider,
        api_key=args.narration_llm_api_key,
        batch_size=args.classification_batch_size,
    )
    if triplets:
        qa._probe_narration_classifier(classifier=classifier)
    bucket_groups = _group_by_bucket(triplets=triplets)
    for bucket_number, (bucket, bucket_triplets) in enumerate(bucket_groups, start=1):
        print(f"Processing bucket {bucket_number}/{len(bucket_groups)}: gs://{bucket}/")
        batches = qa_screen._chunks(bucket_triplets, args.batch_size)
        for batch_number, batch in enumerate(batches, start=1):
            _process_batch(
                args=args,
                client=client,
                dataset=dataset,
                classifier=classifier,
                batch=batch,
                batch_number=batch_number,
                batch_count=len(batches),
            )

    qa_screen.write_dataset_summary(dataset=dataset)


def _process_batch(  # noqa: PLR0913  the orchestration boundary needs the runtime context.
    args: argparse.Namespace,
    client: storage.Client,
    dataset: VideoDataset,
    classifier: narration_classification.OpenAICompatibleNarrationClassifier,
    batch: list[qa_pull.RemoteTriplet],
    batch_number: int,
    batch_count: int,
) -> None:
    print(f"Processing batch {batch_number}/{batch_count} ({len(batch)} delivery(ies))...")
    local = qa_pull.download_triplets(
        client=client,
        triplets=batch,
        destination=args.destination,
    )
    try:
        local = _transcribe_batch(args=args, triplets=local)
        results = qa_screen.screen_deliveries(
            dataset=dataset,
            triplets=local,
            classifier=classifier,
            batch_size=args.batch_size,
            target_fps=args.target_fps,
            force=args.force_classify,
            probe_classifier=False,
        )
        uploaded_urls = _upload_results(
            args=args,
            client=client,
            dataset=dataset,
            triplets=local,
        )
    except Exception:
        print(f"Batch {batch_number} failed; local files remain under {args.destination}.")
        raise

    _print_results(results=results)
    for uploaded_url in uploaded_urls:
        print(f"  Uploaded {uploaded_url}")
    if args.cleanup_local_files:
        deleted = qa_pull.cleanup_triplets(triplets=local, destination=args.destination)
        print(f"Cleaned up {deleted} local file(s) from batch {batch_number}.")


def _upload_results(
    args: argparse.Namespace,
    client: storage.Client,
    dataset: VideoDataset,
    triplets: list[qa_pull.LocalTriplet],
) -> list[str]:
    if not args.apply:
        return []
    return qa_results.upload_result_records(
        client=client,
        dataset=dataset,
        triplets=triplets,
        results_prefix=args.results_prefix,
    )


def _group_by_bucket(
    triplets: list[qa_pull.RemoteTriplet],
) -> list[tuple[str, list[qa_pull.RemoteTriplet]]]:
    by_bucket: dict[str, list[qa_pull.RemoteTriplet]] = {}
    for triplet in triplets:
        by_bucket.setdefault(triplet.bucket, []).append(triplet)
    return list(by_bucket.items())


def _transcribe_batch(
    args: argparse.Namespace,
    triplets: list[qa_pull.LocalTriplet],
) -> list[qa_pull.LocalTriplet]:
    missing = sum(triplet.transcript_path is None for triplet in triplets)
    if not args.transcribe or not missing:
        return triplets
    print(f"Generating {missing} missing transcript(s) with faster-whisper...")
    return qa_transcribe.fill_missing_transcripts(
        triplets=triplets,
        whisper_python=args.whisper_python,
        model=args.whisper_model,
        device=args.whisper_device,
        compute_type=args.whisper_compute_type,
    )


def _print_results(results: list[qa_screen.ScreenResult]) -> None:
    for result in results:
        narration = result.narration_qa_status or "n/a"
        print(f"  [{result.automated_qa_status}] {result.file_name} (narration: {narration})")
        if result.issues:
            print(f"    issues: {result.issues}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default=sampler.DEFAULT_PROJECT)
    parser.add_argument(
        "--bucket", action="append", help="Bucket to pull from. Repeatable. Defaults to discovery."
    )
    parser.add_argument("--bucket-suffix", default=sampler.DEFAULT_BUCKET_SUFFIX)
    parser.add_argument(
        "--work-prefix",
        action="append",
        default=None,
        help=f"Prefix(es) to pull from. Defaults to {qa_pull.DEFAULT_WORK_PREFIXES}.",
    )
    parser.add_argument(
        "--destination",
        type=Path,
        default=Path(tempfile.gettempdir()) / "qa-pull",
        help="Local folder to download triplets into.",
    )
    parser.add_argument(
        "--cleanup-local-files",
        action="store_true",
        help="Delete each batch's local files after QA and requested uploads succeed.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upload completed per-video JSON records to their source buckets.",
    )
    parser.add_argument(
        "--results-prefix",
        default=qa_results.DEFAULT_RESULTS_PREFIX,
        help="Same-bucket prefix for uploaded per-video QA records.",
    )
    parser.add_argument(
        "--max-videos", type=int, default=None, help="Pull at most this many triplets."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List discoverable deliveries without downloading."
    )
    parser.add_argument(
        "--no-transcribe",
        dest="transcribe",
        action="store_false",
        help="Skip faster-whisper transcription for videos that shipped without a transcript.",
    )
    parser.add_argument("--whisper-python", type=Path, default=qa_transcribe.DEFAULT_WHISPER_PYTHON)
    parser.add_argument("--whisper-model", default=qa_transcribe.DEFAULT_WHISPER_MODEL)
    parser.add_argument("--whisper-device", default=qa_transcribe.DEFAULT_WHISPER_DEVICE)
    parser.add_argument(
        "--whisper-compute-type", default=qa_transcribe.DEFAULT_WHISPER_COMPUTE_TYPE
    )
    parser.add_argument(
        "--db-file",
        type=Path,
        default=Path(tempfile.gettempdir()) / "qa-screen.db",
        help="Persistent DuckDB database the screened dataset is kept in.",
    )
    parser.add_argument("--dataset-name", default="egocentric-qa")
    parser.add_argument(
        "--target-fps",
        type=float,
        default=qa_screen.DEFAULT_TARGET_FPS,
        help="Frame rate videos are subsampled to at ingest (keeps the database small).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=qa_screen.DEFAULT_BATCH_SIZE,
        help="Deliveries downloaded, screened, and optionally cleaned up per batch.",
    )
    parser.add_argument("--narration-llm-base-url", default=qa.DEFAULT_NARRATION_LLM_BASE_URL)
    parser.add_argument("--narration-llm-model", default=qa_screen.DEFAULT_NARRATION_MODEL)
    parser.add_argument("--narration-llm-provider", default=qa.DEFAULT_NARRATION_LLM_PROVIDER)
    parser.add_argument("--narration-llm-api-key", default=qa.DEFAULT_NARRATION_LLM_API_KEY)
    parser.add_argument(
        "--classification-batch-size", type=int, default=qa_screen.DEFAULT_BATCH_SIZE
    )
    parser.add_argument(
        "--force-classify",
        action="store_true",
        help="Reclassify narration and republish even if a result record already exists.",
    )
    args = parser.parse_args()
    if args.work_prefix is None:
        args.work_prefix = list(qa_pull.DEFAULT_WORK_PREFIXES)
    return args


if __name__ == "__main__":
    main()
