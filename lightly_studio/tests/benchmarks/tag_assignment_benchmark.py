"""Bulk tag-assignment micro-benchmark.

Measures the database code path that LIG-9850 optimizes: assigning a tag to many
samples via ``tag_resolver.add_sample_ids_to_tag_id``. It reports wall-clock time
and peak Python allocation (``tracemalloc``) for each phase, on either a temporary
DuckDB file (default) or PostgreSQL (``--postgres``).

The original implementation called ``session.merge`` once per sample id (one
round-trip each), so assigning a tag to N samples took N statements and the GUI
"add to tag" action could run for minutes. The ``assign`` phase is where that cost
shows up; the ``reassign`` phase repeats the call with the same ids to exercise the
idempotent conflict-handling path (already-tagged samples).

Run from the ``lightly_studio`` directory:

    uv run tests/benchmarks/tag_assignment_benchmark.py

Against PostgreSQL:

    make start-postgres
    uv run tests/benchmarks/tag_assignment_benchmark.py --postgres
    make stop-postgres
"""

from __future__ import annotations

import argparse
import os
import time
import tracemalloc
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from sqlalchemy import func
from sqlmodel import select
from tqdm import tqdm

from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.sample import SampleCreate, SampleTagLinkTable
from lightly_studio.models.tag import TagCreate
from lightly_studio.resolvers import (
    collection_resolver,
    sample_resolver,
    tag_resolver,
)

DEFAULT_NUM_SAMPLES = 100_000
DEFAULT_DATASET_NAME = "tag_assignment_benchmark"
DEFAULT_TAG_NAME = "benchmark_tag"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"

_BYTES_PER_MIB = 1024 * 1024


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for the tag-assignment benchmark."""

    num_samples: int
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
    """Run the assign and reassign benchmarks and print a report."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_samples=args.num_samples,
        postgres=args.postgres,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_tag_assignment_benchmark_") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.db"
        db_target = _connect_database(db_path=db_path, use_postgres=config.postgres)

        try:
            sample_ids, tag_id = _setup(config=config)

            assign_result = _run_assign_benchmark(
                name="assign", sample_ids=sample_ids, tag_id=tag_id
            )
            reassign_result = _run_assign_benchmark(
                name="reassign", sample_ids=sample_ids, tag_id=tag_id
            )
            linked_count = _count_links(tag_id=tag_id)
        finally:
            db_manager.close()

    _verify_idempotency(linked_count=linked_count, expected=config.num_samples)
    _print_report(
        config=config,
        db_target=db_target,
        results=[assign_result, reassign_result],
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-samples", type=int, default=DEFAULT_NUM_SAMPLES)
    parser.add_argument(
        "--postgres",
        action="store_true",
        help=(
            "Benchmark against PostgreSQL instead of a temporary DuckDB file. "
            "Uses $LIGHTLY_STUDIO_DATABASE_URL if set, otherwise "
            f"{DEFAULT_POSTGRES_URL}."
        ),
    )
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_samples <= 0:
        raise ValueError("--num-samples must be greater than zero.")


def _connect_database(db_path: Path, use_postgres: bool) -> str:
    """Connect to a fresh database and return a description of its target."""
    db_manager.close()
    if use_postgres:
        database_url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
        db_manager.connect(db_url=database_url, cleanup_existing=True)
        return database_url
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)
    return str(db_path)


def _setup(config: BenchmarkConfig) -> tuple[list[UUID], UUID]:
    """Create the collection, empty samples to tag, and the target tag.

    Returns the created sample ids and the tag id. Samples are inserted via the
    regular resolver path so the foreign key on ``SampleTagLinkTable.sample_id`` is
    satisfiable.
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
        tag = tag_resolver.create(
            session=session,
            tag=TagCreate(
                name=DEFAULT_TAG_NAME,
                collection_id=collection.collection_id,
                kind="sample",
            ),
        )
        return sample_ids, tag.tag_id


def _run_assign_benchmark(
    name: str,
    sample_ids: list[UUID],
    tag_id: UUID,
) -> PhaseResult:
    """Assign the tag to all sample ids via the resolver path under measurement."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()

    with (
        db_manager.session() as session,
        tqdm(total=len(sample_ids), desc=name.capitalize(), unit=" samples") as progress,
    ):
        tag_resolver.add_sample_ids_to_tag_id(session=session, tag_id=tag_id, sample_ids=sample_ids)
        progress.update(len(sample_ids))

    elapsed = time.perf_counter() - started
    peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
    tracemalloc.stop()
    return PhaseResult(name=name, wall_seconds=elapsed, peak_mib=peak_mib, count=len(sample_ids))


def _count_links(tag_id: UUID) -> int:
    """Count the sample-tag links for the tag (to confirm no duplicates were created)."""
    with db_manager.session() as session:
        count = session.exec(
            select(func.count())
            .select_from(SampleTagLinkTable)
            .where(SampleTagLinkTable.tag_id == tag_id)
        ).one()
        return int(count)


def _verify_idempotency(linked_count: int, expected: int) -> None:
    """Fail loudly if reassigning the same ids created duplicate links."""
    if linked_count != expected:
        raise ValueError(
            f"Expected {expected} sample-tag links after reassign, found {linked_count}. "
            "Idempotency is broken."
        )


def _print_report(
    config: BenchmarkConfig,
    db_target: str,
    results: list[PhaseResult],
) -> None:
    """Print a compact, copy-pasteable results block."""
    backend = "postgres" if config.postgres else "duckdb"
    print("")
    print("Tag assignment benchmark")
    print(f"  backend={backend} db={db_target} num_samples={config.num_samples}")
    for result in results:
        print(
            f"  {result.name:<9} "
            f"time={result.wall_seconds:8.3f}s "
            f"throughput={result.per_second:10.1f}/s "
            f"peak_python_mem={result.peak_mib:8.1f} MiB"
        )


if __name__ == "__main__":
    main()
