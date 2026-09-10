"""Metadata write/query micro-benchmark.

Measures the database code paths that LIG-10789 (JSON to JSONB on PostgreSQL) affects:
writing metadata via ``metadata_resolver.bulk_update_metadata`` and reading it back through
the aggregation resolvers the GUI sidebar fires on load, each of which extracts JSON keys from
every metadata row:

- ``get_metadata_info.get_all_metadata_keys_and_schema`` (the ``/metadata/info`` endpoint,
  flagged as slow in LIG-10726),
- ``get_metadata_info.get_metadata_histograms`` (numeric value distributions),
- ``categorical_value_counts.get_metadata_value_counts`` (categorical value counts).

It reports wall-clock time and peak Python allocation (``tracemalloc``) for each phase, on either
a temporary DuckDB file (default) or PostgreSQL (``--postgres``). JSONB only applies to PostgreSQL,
so run with ``--postgres`` on this branch and on ``main`` to compare json vs jsonb read times.

To simulate a BRT-scale metadata load, the benchmark seeds many samples, each with several numeric
and several categorical keys, for ``num_samples * (num_numeric_keys + num_categorical_keys)``
key-value pairs in total.

Run from the ``lightly_studio`` directory:

    uv run tests/benchmarks/metadata_query_benchmark.py

Against PostgreSQL (where the JSONB change applies):

    make start-postgres
    uv run tests/benchmarks/metadata_query_benchmark.py --postgres
    make stop-postgres

A quick smoke-test with a smaller dataset:

    uv run tests/benchmarks/metadata_query_benchmark.py --num-samples 10000
"""

from __future__ import annotations

import argparse
import os
import time
import tracemalloc
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable
from uuid import UUID

import numpy as np
from tqdm import tqdm

from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.sample import SampleCreate
from lightly_studio.resolvers import (
    collection_resolver,
    metadata_resolver,
    sample_resolver,
)
from lightly_studio.resolvers.metadata_resolver.sample import (
    categorical_value_counts,
    get_metadata_info,
)
from lightly_studio.utils import batching

DEFAULT_NUM_SAMPLES = 100_000
DEFAULT_NUM_NUMERIC_KEYS = 8
DEFAULT_NUM_CATEGORICAL_KEYS = 8
DEFAULT_NUM_CATEGORIES = 10
DEFAULT_WRITE_BATCH_SIZE = 5_000
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "metadata_query_benchmark"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"

_BYTES_PER_MIB = 1024 * 1024


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for the metadata query benchmark."""

    num_samples: int
    num_numeric_keys: int
    num_categorical_keys: int
    num_categories: int
    write_batch_size: int
    seed: int
    postgres: bool


@dataclass(frozen=True)
class PhaseResult:
    """Wall-clock time and peak Python allocation for a single phase."""

    name: str
    wall_seconds: float
    peak_mib: float
    count: int

    @property
    def per_second(self) -> float:
        """Throughput in samples per second."""
        return self.count / self.wall_seconds if self.wall_seconds > 0 else float("inf")


def main() -> None:
    """Run the write and query benchmarks and print a report."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_samples=args.num_samples,
        num_numeric_keys=args.num_numeric_keys,
        num_categorical_keys=args.num_categorical_keys,
        num_categories=args.num_categories,
        write_batch_size=args.write_batch_size,
        seed=args.seed,
        postgres=args.postgres,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_metadata_query_benchmark_") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.db"
        db_target = _connect_database(db_path=db_path, use_postgres=config.postgres)

        try:
            collection_id, sample_ids = _setup(config=config)
            metadata_rows = _generate_metadata(config=config)

            write_result = _run_write_benchmark(
                config=config, sample_ids=sample_ids, metadata_rows=metadata_rows
            )
            read_results = _run_read_benchmarks(config=config, collection_id=collection_id)
        finally:
            db_manager.close()

    _print_report(config=config, db_target=db_target, results=[write_result, *read_results])


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-samples", type=int, default=DEFAULT_NUM_SAMPLES)
    parser.add_argument("--num-numeric-keys", type=int, default=DEFAULT_NUM_NUMERIC_KEYS)
    parser.add_argument("--num-categorical-keys", type=int, default=DEFAULT_NUM_CATEGORICAL_KEYS)
    parser.add_argument("--num-categories", type=int, default=DEFAULT_NUM_CATEGORIES)
    parser.add_argument("--write-batch-size", type=int, default=DEFAULT_WRITE_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--postgres",
        action="store_true",
        help=(
            "Benchmark against PostgreSQL (where the JSONB change applies) instead of a temporary "
            "DuckDB file. Uses $LIGHTLY_STUDIO_DATABASE_URL if set, otherwise "
            f"{DEFAULT_POSTGRES_URL}."
        ),
    )
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_samples <= 0:
        raise ValueError("--num-samples must be greater than zero.")
    if config.num_numeric_keys < 0:
        raise ValueError("--num-numeric-keys must not be negative.")
    if config.num_categorical_keys < 0:
        raise ValueError("--num-categorical-keys must not be negative.")
    if config.num_numeric_keys + config.num_categorical_keys == 0:
        raise ValueError("At least one metadata key is required.")
    if config.num_categories <= 0:
        raise ValueError("--num-categories must be greater than zero.")
    if config.write_batch_size <= 0:
        raise ValueError("--write-batch-size must be greater than zero.")


def _connect_database(db_path: Path, use_postgres: bool) -> str:
    """Connect to a fresh database and return a description of its target."""
    db_manager.close()
    if use_postgres:
        database_url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
        db_manager.connect(db_url=database_url, cleanup_existing=True)
        return database_url
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)
    return str(db_path)


def _setup(config: BenchmarkConfig) -> tuple[UUID, list[UUID]]:
    """Create the collection and empty samples that the metadata attaches to.

    Returns the collection id and the created sample ids.
    """
    with db_manager.session() as session:
        collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(
                name=DEFAULT_DATASET_NAME,
                sample_type=SampleType.IMAGE,
            ),
        )
        sample_ids = sample_resolver.create_many(
            session=session,
            samples=[
                SampleCreate(collection_id=collection.collection_id)
                for _ in range(config.num_samples)
            ],
        )
        return collection.collection_id, sample_ids


def _generate_metadata(config: BenchmarkConfig) -> list[dict[str, Any]]:
    """Generate deterministic per-sample metadata dicts with numeric and categorical keys."""
    rng = np.random.default_rng(config.seed)
    numeric_values = rng.random((config.num_samples, config.num_numeric_keys))
    categorical_values = rng.integers(
        0, config.num_categories, (config.num_samples, config.num_categorical_keys)
    )
    rows: list[dict[str, Any]] = []
    for sample_index in range(config.num_samples):
        row: dict[str, Any] = {
            f"numeric_{key_index}": float(numeric_values[sample_index, key_index])
            for key_index in range(config.num_numeric_keys)
        }
        for key_index in range(config.num_categorical_keys):
            row[f"category_{key_index}"] = f"value_{categorical_values[sample_index, key_index]}"
        rows.append(row)
    return rows


def _run_write_benchmark(
    config: BenchmarkConfig,
    sample_ids: list[UUID],
    metadata_rows: list[dict[str, Any]],
) -> PhaseResult:
    """Write metadata for every sample via the bulk resolver path."""
    sample_metadata: list[tuple[UUID, Mapping[str, Any]]] = list(zip(sample_ids, metadata_rows))
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()

    with (
        db_manager.session() as session,
        tqdm(total=len(sample_metadata), desc="Writing", unit=" samples") as progress,
    ):
        for batch in batching.batched(items=sample_metadata, batch_size=config.write_batch_size):
            metadata_resolver.bulk_update_metadata(session=session, sample_metadata=list(batch))
            progress.update(len(batch))

    elapsed = time.perf_counter() - started
    peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
    tracemalloc.stop()
    return PhaseResult(
        name="write", wall_seconds=elapsed, peak_mib=peak_mib, count=len(sample_metadata)
    )


def _run_read_benchmarks(config: BenchmarkConfig, collection_id: UUID) -> list[PhaseResult]:
    """Run each aggregation read path and return its phase result."""
    read_phases: list[tuple[str, Callable[..., Any]]] = [
        ("metadata_info", get_metadata_info.get_all_metadata_keys_and_schema),
        ("histograms", get_metadata_info.get_metadata_histograms),
        ("value_counts", categorical_value_counts.get_metadata_value_counts),
    ]
    return [
        _run_read_benchmark(name=name, read_fn=read_fn, config=config, collection_id=collection_id)
        for name, read_fn in read_phases
    ]


def _run_read_benchmark(
    name: str,
    read_fn: Callable[..., Any],
    config: BenchmarkConfig,
    collection_id: UUID,
) -> PhaseResult:
    """Run one aggregation read path over all metadata rows and measure it."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()

    with db_manager.session() as session:
        result = read_fn(session=session, collection_id=collection_id)
        if not result:
            raise ValueError(f"Read phase '{name}' returned no metadata.")

    elapsed = time.perf_counter() - started
    peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
    tracemalloc.stop()
    return PhaseResult(name=name, wall_seconds=elapsed, peak_mib=peak_mib, count=config.num_samples)


def _print_report(
    config: BenchmarkConfig,
    db_target: str,
    results: list[PhaseResult],
) -> None:
    """Print a compact, copy-pasteable results block."""
    backend = "postgres" if config.postgres else "duckdb"
    keys_per_sample = config.num_numeric_keys + config.num_categorical_keys
    print("")
    print("Metadata query benchmark")
    print(
        f"  backend={backend} db={db_target} "
        f"num_samples={config.num_samples} keys_per_sample={keys_per_sample} "
        f"(numeric={config.num_numeric_keys} categorical={config.num_categorical_keys})"
    )
    for result in results:
        print(
            f"  {result.name:<13} "
            f"time={result.wall_seconds:8.3f}s "
            f"throughput={result.per_second:10.1f}/s "
            f"peak_python_mem={result.peak_mib:8.1f} MiB"
        )


if __name__ == "__main__":
    main()
