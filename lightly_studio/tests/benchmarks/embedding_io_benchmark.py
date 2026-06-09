"""Embedding insert/load micro-benchmark.

Measures the database code paths that LIG-8101 optimizes: inserting sample
embeddings via ``sample_embedding_resolver.create_many`` and loading them back
via ``sample_embedding_resolver.get_by_sample_ids``. It reports wall-clock time
and peak Python allocation (``tracemalloc``) for each phase, on either a
temporary DuckDB file (default) or PostgreSQL (``--postgres``).

The peak-memory figure is the signal for the ``list[list[float]]`` problem
described in LIG-8101: each Python ``float`` in a list costs ~50 B versus 4 B in
a numpy ``float32`` buffer, so the load phase is where a numpy representation
should show the largest win.

Run from the ``lightly_studio`` directory:

    uv run tests/benchmarks/embedding_io_benchmark.py

Against PostgreSQL (pgvector):

    make start-postgres
    uv run tests/benchmarks/embedding_io_benchmark.py --postgres
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

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from lightly_studio import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import (
    collection_resolver,
    embedding_model_resolver,
    sample_embedding_resolver,
    sample_resolver,
)
from lightly_studio.utils import batching

DEFAULT_NUM_EMBEDDINGS = 100_000
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_INSERT_BATCH_SIZE = 1_024
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "embedding_io_benchmark"
DEFAULT_EMBEDDING_MODEL_NAME = "benchmark_embeddings"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"

_BYTES_PER_MIB = 1024 * 1024


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for the embedding I/O benchmark."""

    num_embeddings: int
    embedding_dim: int
    insert_batch_size: int
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
        """Throughput in embeddings per second."""
        return self.count / self.wall_seconds if self.wall_seconds > 0 else float("inf")


def main() -> None:
    """Run the insert and load benchmarks and print a report."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_embeddings=args.num_embeddings,
        embedding_dim=args.embedding_dim,
        insert_batch_size=args.insert_batch_size,
        seed=args.seed,
        postgres=args.postgres,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_embedding_io_benchmark_") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.db"
        db_target = _connect_database(db_path=db_path, use_postgres=config.postgres)

        try:
            sample_ids, embedding_model_id = _setup(config=config)
            embeddings = _generate_embeddings(config=config)

            insert_result = _run_insert_benchmark(
                config=config,
                sample_ids=sample_ids,
                embedding_model_id=embedding_model_id,
                embeddings=embeddings,
            )
            load_result = _run_load_benchmark(
                sample_ids=sample_ids,
                embedding_model_id=embedding_model_id,
            )
        finally:
            db_manager.close()

    _print_report(
        config=config,
        db_target=db_target,
        results=[insert_result, load_result],
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-embeddings", type=int, default=DEFAULT_NUM_EMBEDDINGS)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--insert-batch-size", type=int, default=DEFAULT_INSERT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--postgres",
        action="store_true",
        help=(
            "Benchmark against PostgreSQL (pgvector) instead of a temporary DuckDB file. "
            "Uses $LIGHTLY_STUDIO_DATABASE_URL if set, otherwise "
            f"{DEFAULT_POSTGRES_URL}."
        ),
    )
    return parser.parse_args()


def _validate_config(config: BenchmarkConfig) -> None:
    """Validate the benchmark configuration."""
    if config.num_embeddings <= 0:
        raise ValueError("--num-embeddings must be greater than zero.")
    if config.embedding_dim <= 0:
        raise ValueError("--embedding-dim must be greater than zero.")
    if config.insert_batch_size <= 0:
        raise ValueError("--insert-batch-size must be greater than zero.")


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
    """Create the collection, embedding model, and empty samples to embed.

    Returns the created sample ids and the embedding model id. Samples are
    inserted via the regular resolver path so the foreign keys on
    ``sample_embedding`` are satisfiable.
    """
    with db_manager.session() as session:
        collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(
                name=DEFAULT_DATASET_NAME,
                sample_type=SampleType.IMAGE,
            ),
        )
        embedding_model = embedding_model_resolver.create(
            session=session,
            embedding_model=EmbeddingModelCreate(
                collection_id=collection.collection_id,
                name=DEFAULT_EMBEDDING_MODEL_NAME,
                embedding_dimension=config.embedding_dim,
            ),
        )
        sample_ids = sample_resolver.create_many(
            session=session,
            samples=[
                SampleCreate(collection_id=collection.collection_id)
                for _ in range(config.num_embeddings)
            ],
        )
        return sample_ids, embedding_model.embedding_model_id


def _generate_embeddings(config: BenchmarkConfig) -> NDArray[np.float32]:
    """Generate deterministic random float32 embeddings."""
    rng = np.random.default_rng(config.seed)
    return rng.random((config.num_embeddings, config.embedding_dim), dtype=np.float32)


def _run_insert_benchmark(
    config: BenchmarkConfig,
    sample_ids: list[UUID],
    embedding_model_id: UUID,
    embeddings: NDArray[np.float32],
) -> PhaseResult:
    """Insert embeddings via the resolver path, mirroring EmbeddingManager._store_embeddings."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()

    with (
        db_manager.session() as session,
        tqdm(total=len(sample_ids), desc="Inserting", unit=" embeddings") as progress,
    ):
        for batch in batching.batched(
            items=zip(sample_ids, embeddings), batch_size=config.insert_batch_size
        ):
            sample_embeddings = [
                SampleEmbeddingCreate(
                    sample_id=sample_id,
                    embedding_model_id=embedding_model_id,
                    embedding=embedding,
                )
                for sample_id, embedding in batch
            ]
            sample_embedding_resolver.create_many(
                session=session, sample_embeddings=sample_embeddings
            )
            progress.update(len(sample_embeddings))

    elapsed = time.perf_counter() - started
    peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
    tracemalloc.stop()
    return PhaseResult(
        name="insert", wall_seconds=elapsed, peak_mib=peak_mib, count=len(sample_ids)
    )


def _run_load_benchmark(
    sample_ids: list[UUID],
    embedding_model_id: UUID,
) -> PhaseResult:
    """Load embeddings back and fully materialize them, mirroring the selection read path."""
    tracemalloc.start()
    tracemalloc.reset_peak()
    started = time.perf_counter()

    with db_manager.session() as session:
        loaded = sample_embedding_resolver.get_by_sample_ids(
            session=session,
            sample_ids=sample_ids,
            embedding_model_id=embedding_model_id,
        )
        # Touch every vector so the full in-memory representation is realized
        # (this is where list[float] is far heavier than a numpy buffer).
        for row in loaded:
            if len(row.embedding) == 0:
                raise ValueError("Loaded an empty embedding.")

    elapsed = time.perf_counter() - started
    peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
    tracemalloc.stop()
    return PhaseResult(name="load", wall_seconds=elapsed, peak_mib=peak_mib, count=len(loaded))


def _print_report(
    config: BenchmarkConfig,
    db_target: str,
    results: list[PhaseResult],
) -> None:
    """Print a compact, copy-pasteable results block."""
    backend = "postgres" if config.postgres else "duckdb"
    print("")
    print("Embedding I/O benchmark")
    print(
        f"  backend={backend} db={db_target} "
        f"num_embeddings={config.num_embeddings} dim={config.embedding_dim} "
        f"insert_batch_size={config.insert_batch_size}"
    )
    for result in results:
        print(
            f"  {result.name:<7} "
            f"time={result.wall_seconds:8.3f}s "
            f"throughput={result.per_second:10.1f}/s "
            f"peak_python_mem={result.peak_mib:8.1f} MiB"
        )


if __name__ == "__main__":
    main()
