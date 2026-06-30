"""Benchmark consuming the Open Images *train* split (~1,743,042 images).

Streams straight from the public S3 bucket and measures the two phases of
ingestion separately, so it's clear where the time goes at 1M+ scale:

    1. Discovery  - listing object keys (parallel prefix fan-out).
    2. Processing - creating sample rows in the database.

By default it runs the fastest possible index: no embeddings, no per-image
dimension reads, parallel cloud listing. The image paths (incl. the Open Images
ID) are stored, so dimensions/embeddings can be backfilled later.

Run:
    pip install "lightly-studio[cloud-storage]"
    uv run e2e-tests/benchmark_train.py

Quick run on a slice first (recommended before the full 1.74M):
    OI_LIMIT=100000 uv run e2e-tests/benchmark_train.py

Env knobs:
    OI_SPLIT         train | test | validation        (default: train)
    OI_LIST_WORKERS  concurrent listing workers        (default: 64)
    OI_LIMIT         cap number of images consumed     (default: all)
    OI_READ_DIMS     "1" to also read width/height     (default: 0 = skip)
Also honored: LIGHTLY_STUDIO_LOADER_WORKERS, LIGHTLY_STUDIO_LIST_PREFIXES.

Embeddings are a separate, much heavier step (they read every image and need a
model) and are intentionally out of scope here — this measures how fast the
dataset can be *consumed* (listed + registered).
"""

from __future__ import annotations

import itertools
import os
import time

import fsspec

# Open Images object names are 16-char lowercase-hex IDs, so fan the listing out
# across 256 two-character hex prefixes (set before the lister reads these).
os.environ.setdefault("LIGHTLY_STUDIO_LIST_PREFIXES", "0123456789abcdef")
os.environ.setdefault("LIGHTLY_STUDIO_LIST_PREFIX_DEPTH", "2")

from lightly_studio.core.image import add_images
from lightly_studio.core.image.image_dataset import ImageDataset
from lightly_studio.database import db_manager
from lightly_studio.dataset import fsspec_lister

# Public, anonymous bucket; raise the connection pool so concurrent reads/listing
# are not throttled by botocore's default of 10, and cap read-ahead.
fsspec.config.conf["s3"] = {
    "anon": True,
    "default_block_size": 64 * 1024,
    "config_kwargs": {"max_pool_connections": 256},
}


def _env_int(name: str, default: int | None) -> int | None:
    value = os.environ.get(name, "")
    return int(value) if value else default


def main() -> None:
    split = os.environ.get("OI_SPLIT", "train")
    path = f"s3://open-images-dataset/{split}/"
    # Default matches the 256 two-character hex prefixes, so every prefix lists at once.
    list_workers = _env_int("OI_LIST_WORKERS", 256) or 256
    limit = _env_int("OI_LIMIT", None)
    read_dims = os.environ.get("OI_READ_DIMS", "0") == "1"

    print(
        f"\nConsuming {path}\n"
        f"  list_workers={list_workers}  read_dimensions={read_dims}"
        f"  limit={limit if limit is not None else 'all'}\n"
    )

    db_manager.connect(db_file="lightly_studio.db", cleanup_existing=True)
    dataset = ImageDataset.create(name=f"open_images_{split}")

    # --- Phase 1: discovery (listing object keys) ---
    t0 = time.perf_counter()
    paths_iter = fsspec_lister.iter_files_from_path(path=path, list_workers=list_workers)
    if limit is not None:
        paths_iter = itertools.islice(paths_iter, limit)
    image_paths = list(paths_iter)
    t_list = time.perf_counter() - t0
    n = len(image_paths)
    rate_list = n / t_list if t_list else 0
    print(f"[discovery]  {n:>9,} files     in {t_list:8.1f}s  ->  {rate_list:>10,.0f} files/s")

    # --- Phase 2: processing (sample-row creation) ---
    t0 = time.perf_counter()
    created = add_images.load_into_dataset_from_paths(
        session=dataset.session,
        root_collection_id=dataset.collection_id,
        image_paths=image_paths,
        read_dimensions=read_dims,
    )
    t_proc = time.perf_counter() - t0
    rate_proc = len(created) / t_proc if t_proc else 0
    print(f"[processing] {len(created):>9,} samples   in {t_proc:8.1f}s  ->  {rate_proc:>10,.0f} samples/s")

    total = t_list + t_proc
    rate_total = n / total if total else 0
    print(f"[total]      {n:>9,} images    in {total:8.1f}s  ->  {rate_total:>10,.0f} images/s\n")


if __name__ == "__main__":
    main()
