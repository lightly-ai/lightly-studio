"""2D embedding loading micro-benchmark.

Measures the database code paths that LIG-10480 optimizes:
``twodim_embedding_resolver.get_twodim_embeddings``, the call behind the embeddings
scatter plot. It reports wall-clock time on either a temporary DuckDB file (default)
or PostgreSQL (``--postgres``).

The original implementation keyed the ``two_dim_embeddings`` cache on a SHA-256 digest
over the first dimension of every embedding. Building that key meant reading every
embedding in the collection, so even a cache *hit* paid for the full read. The digest
is now an md5 over the sample ids, computed in the database, and the cache is keyed on
``(collection_id, embedding_model_id)`` with the sample ids stored in the row.

On PostgreSQL the old form cost far more than it looks: pgvector stores a 512-dim
vector out of line, so reading one dimension detoasts the whole vector, once per row.
DuckDB keeps the arrays inline and may show little difference, so run the
baseline/after comparison with ``--postgres`` to see the real effect.

Phases:

* ``cold`` populates the cache: fingerprint, full embedding read, PaCMAP projection, and
  the cache write. Reported for context only and deliberately untimed as a headline --
  the projection dominates it and no part of this change touches the projection.
* ``warm`` reads back through the populated cache, once per ``--repeats``, each in a
  fresh session so no timing benefits from SQLAlchemy's identity map. This is the
  number to compare across branches, reported as a median with min/max.

Comparing against the base commit is the point of this file, so it calls nothing but
``get_twodim_embeddings``. That function has the same signature before and after the
change, so the file runs unmodified on both sides. Referring to ``TwoDimEmbeddingTable``
or either fingerprint helper would break that, as all of them were reshaped.

The default is one million samples, which is the scale the scatter plot has to survive.
Budget around 20 minutes per run at that size and a few GB of memory: inserting a million
512-dim vectors takes a few minutes, and the PaCMAP projection in the cold phase takes
roughly 15 more. Only the cold phase is that slow, and it is the part no branch changes.
Pass a smaller ``--num-samples`` (20000 finishes in well under a minute) for a quick
check; the warm comparison holds at any size as long as both sides use the same value.

Run from the ``lightly_studio`` directory:

    uv run tests/benchmarks/twodim_embedding_benchmark.py

Against PostgreSQL (pgvector):

    make start-postgres
    uv run tests/benchmarks/twodim_embedding_benchmark.py --postgres
    make stop-postgres

To compare against the base commit, copy this file over and run it there:

    git worktree add /tmp/ls-base 7a681fe8
    cp tests/benchmarks/twodim_embedding_benchmark.py /tmp/ls-base/lightly_studio/tests/benchmarks/
    cd /tmp/ls-base/lightly_studio
    uv run tests/benchmarks/twodim_embedding_benchmark.py --postgres

Both sides must use the same ``--num-samples``, and must not share a database. DuckDB is
safe by construction: each run builds a fresh file from the SQLModel metadata and never
runs Alembic, so a file written by one branch is never seen by the other.

PostgreSQL needs one manual step when switching branches. ``cleanup_existing=True`` drops
the tables through ``SQLModel.metadata``, which only lists the tables the *running*
branch knows about. The reshaped ``two_dim_embeddings`` adds a foreign key to
``embedding_model``, so the older branch cannot drop ``embedding_model`` and the run
fails. Reset the schema between the two runs:

    docker exec -e PGPASSWORD=lightly lightly-studio-postgres psql -U lightly -d
    lightly_studio -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public; GRANT ALL ON
    SCHEMA public TO lightly; GRANT ALL ON SCHEMA public TO public;"

(as one line -- this is the same reset that ``make migration-check-postgresql`` runs).
"""

from __future__ import annotations

import argparse
import os
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from tqdm import tqdm

from lightly_studio.database import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.sample import SampleCreate
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import (
    collection_resolver,
    embedding_model_resolver,
    sample_embedding_resolver,
    sample_resolver,
    twodim_embedding_resolver,
)
from lightly_studio.utils import batching

DEFAULT_NUM_SAMPLES = 1_000_000
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_INSERT_BATCH_SIZE = 1_024
DEFAULT_REPEATS = 5
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "twodim_embedding_benchmark"
DEFAULT_EMBEDDING_MODEL_NAME = "benchmark_embeddings"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"


@dataclass(frozen=True)
class BenchmarkConfig:
    """Configuration for the 2D embedding benchmark."""

    num_samples: int
    embedding_dim: int
    insert_batch_size: int
    repeats: int
    seed: int
    postgres: bool


@dataclass(frozen=True)
class WarmResult:
    """Wall-clock times for the repeated warm reads."""

    seconds: list[float]

    @property
    def median(self) -> float:
        """Median wall-clock time across the repeats."""
        return statistics.median(self.seconds)


def main() -> None:
    """Run the cold and warm phases and print a report."""
    args = _parse_args()
    config = BenchmarkConfig(
        num_samples=args.num_samples,
        embedding_dim=args.embedding_dim,
        insert_batch_size=args.insert_batch_size,
        repeats=args.repeats,
        seed=args.seed,
        postgres=args.postgres,
    )
    _validate_config(config=config)

    with TemporaryDirectory(prefix="lightly_studio_twodim_embedding_benchmark_") as tmp_dir:
        db_path = Path(tmp_dir) / "benchmark.db"
        db_target = _connect_database(db_path=db_path, use_postgres=config.postgres)

        try:
            collection_id, embedding_model_id = _setup(config=config)
            cold_seconds = _run_once(
                collection_id=collection_id,
                embedding_model_id=embedding_model_id,
                expected_count=config.num_samples,
            )
            warm_result = _run_warm_benchmark(
                config=config,
                collection_id=collection_id,
                embedding_model_id=embedding_model_id,
            )
        finally:
            db_manager.close()

    _print_report(
        config=config,
        db_target=db_target,
        cold_seconds=cold_seconds,
        warm_result=warm_result,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-samples", type=int, default=DEFAULT_NUM_SAMPLES)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--insert-batch-size", type=int, default=DEFAULT_INSERT_BATCH_SIZE)
    parser.add_argument(
        "--repeats",
        type=int,
        default=DEFAULT_REPEATS,
        help="Number of warm reads to time. The report shows their median, min and max.",
    )
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
    if config.num_samples <= 0:
        raise ValueError("--num-samples must be greater than zero.")
    if config.embedding_dim <= 0:
        raise ValueError("--embedding-dim must be greater than zero.")
    if config.insert_batch_size <= 0:
        raise ValueError("--insert-batch-size must be greater than zero.")
    if config.repeats <= 0:
        raise ValueError("--repeats must be greater than zero.")


def _connect_database(db_path: Path, use_postgres: bool) -> str:
    """Connect to a fresh database and return a description of its target."""
    db_manager.close()
    if use_postgres:
        database_url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
        db_manager.connect(db_url=database_url, cleanup_existing=True)
        return database_url
    db_manager.connect(db_file=str(db_path), cleanup_existing=True)
    return str(db_path)


def _setup(config: BenchmarkConfig) -> tuple[UUID, UUID]:
    """Create a collection whose samples all have embeddings.

    Insertion is unmeasured setup. Returns the collection and embedding model ids.
    """
    with db_manager.session() as session:
        collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(name=DEFAULT_DATASET_NAME, sample_type=SampleType.IMAGE),
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
                for _ in range(config.num_samples)
            ],
        )
        embeddings = _generate_embeddings(config=config)
        batches = batching.batched(
            items=zip(sample_ids, embeddings), batch_size=config.insert_batch_size
        )
        for batch in tqdm(batches, desc="inserting embeddings", unit="batch"):
            sample_embedding_resolver.create_many(
                session=session,
                sample_embeddings=[
                    SampleEmbeddingCreate(
                        sample_id=sample_id,
                        embedding_model_id=embedding_model.embedding_model_id,
                        embedding=embedding,
                    )
                    for sample_id, embedding in batch
                ],
            )
        return collection.collection_id, embedding_model.embedding_model_id


def _generate_embeddings(config: BenchmarkConfig) -> NDArray[np.float32]:
    """Generate deterministic random float32 embeddings of shape (num_samples, dim)."""
    rng = np.random.default_rng(config.seed)
    return rng.random((config.num_samples, config.embedding_dim), dtype=np.float32)


def _run_once(collection_id: UUID, embedding_model_id: UUID, expected_count: int) -> float:
    """Time one ``get_twodim_embeddings`` call and return the elapsed seconds.

    Uses a fresh session so the timing does not benefit from SQLAlchemy's identity map.
    """
    with db_manager.session() as session:
        started = time.perf_counter()
        x_values, y_values, sample_ids = twodim_embedding_resolver.get_twodim_embeddings(
            session=session,
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
        )
        elapsed = time.perf_counter() - started

    # A call that silently returned nothing would look fast, so check the result size.
    if not len(x_values) == len(y_values) == len(sample_ids) == expected_count:
        raise ValueError(
            f"Expected {expected_count} points, got "
            f"x={len(x_values)} y={len(y_values)} sample_ids={len(sample_ids)}."
        )
    return elapsed


def _run_warm_benchmark(
    config: BenchmarkConfig,
    collection_id: UUID,
    embedding_model_id: UUID,
) -> WarmResult:
    """Time repeated reads against the populated cache."""
    seconds = [
        _run_once(
            collection_id=collection_id,
            embedding_model_id=embedding_model_id,
            expected_count=config.num_samples,
        )
        for _ in tqdm(range(config.repeats), desc="warm reads", unit="read")
    ]
    return WarmResult(seconds=seconds)


def _print_report(
    config: BenchmarkConfig,
    db_target: str,
    cold_seconds: float,
    warm_result: WarmResult,
) -> None:
    """Print a compact, copy-pasteable results block."""
    backend = "postgres" if config.postgres else "duckdb"
    print("")
    print("2D embedding benchmark")
    print(
        f"  backend={backend} db={db_target} "
        f"num_samples={config.num_samples} dim={config.embedding_dim} "
        f"repeats={config.repeats}"
    )
    print(f"  cold    time={cold_seconds:8.3f}s  (projection-dominated, context only)")
    print(
        f"  warm  median={warm_result.median:8.3f}s "
        f"min={min(warm_result.seconds):8.3f}s "
        f"max={max(warm_result.seconds):8.3f}s"
    )


if __name__ == "__main__":
    main()
