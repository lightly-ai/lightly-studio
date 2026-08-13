"""2D embedding loading benchmark (DuckDB).

Measures ``twodim_embedding_resolver.get_twodim_embeddings``, the call behind the
embeddings scatter plot, in its two very different states:

* ``cold`` -- the cache is empty. Computes the fingerprint, reads every
  high-dimensional embedding, runs the UMAP projection, and writes the cache row.
  Dominated by the projection, which none of the changes under test touch, so this
  number moves very little and is reported only for context.
* ``warm`` -- the cache is populated. This is the path the changes under test
  improve, and the number to compare across branches.

The script deliberately calls nothing but ``get_twodim_embeddings``. That function has
the same signature before and after the changes, so this file can be copied to the base
commit and run there unmodified -- which is the point, since the comparison is only
meaningful if both sides run identical code. Touching ``TwoDimEmbeddingTable`` or the
fingerprint helper directly would break that, as both were reshaped.

Run from the ``lightly_studio`` directory:

    uv run debug/twodim_embedding_benchmark.py

To compare against the base commit:

    git worktree add /tmp/ls-base 7a681fe8
    mkdir -p /tmp/ls-base/lightly_studio/debug
    cp debug/twodim_embedding_benchmark.py /tmp/ls-base/lightly_studio/debug/
    cd /tmp/ls-base/lightly_studio && uv run debug/twodim_embedding_benchmark.py

Both sides must use the same ``--num-samples``. Each run builds its own temporary
database: DuckDB creates its schema from the SQLModel metadata and never runs Alembic,
so a database made by one branch has that branch's table shape and must not be reused.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

import numpy as np
from numpy.typing import NDArray

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

DEFAULT_NUM_SAMPLES = 10_000
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_SEED = 0
INSERT_BATCH_SIZE = 1_024
COLLECTION_NAME = "twodim_embedding_benchmark"
EMBEDDING_MODEL_NAME = "benchmark_embeddings"


def main() -> None:
    """Run the cold and warm phases and print the timings."""
    args = _parse_args()
    if args.num_samples <= 0:
        raise ValueError("--num-samples must be greater than zero.")

    with TemporaryDirectory(prefix="lightly_studio_twodim_embedding_benchmark_") as tmp_dir:
        db_manager.close()
        db_manager.connect(db_file=str(Path(tmp_dir) / "benchmark.db"), cleanup_existing=True)
        try:
            collection_id, embedding_model_id = _setup(
                num_samples=args.num_samples,
                embedding_dim=args.embedding_dim,
                seed=args.seed,
            )
            cold_seconds = _run_phase(
                collection_id=collection_id,
                embedding_model_id=embedding_model_id,
                expected_count=args.num_samples,
            )
            warm_seconds = _run_phase(
                collection_id=collection_id,
                embedding_model_id=embedding_model_id,
                expected_count=args.num_samples,
            )
        finally:
            db_manager.close()

    _print_report(
        num_samples=args.num_samples,
        cold_seconds=cold_seconds,
        warm_seconds=warm_seconds,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--num-samples", type=int, default=DEFAULT_NUM_SAMPLES)
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _setup(num_samples: int, embedding_dim: int, seed: int) -> tuple[UUID, UUID]:
    """Create a collection of samples that all have embeddings.

    Insertion is unmeasured setup. Returns the collection and embedding model ids.
    """
    with db_manager.session() as session:
        collection = collection_resolver.create(
            session=session,
            collection=CollectionCreate(name=COLLECTION_NAME, sample_type=SampleType.IMAGE),
        )
        embedding_model = embedding_model_resolver.create(
            session=session,
            embedding_model=EmbeddingModelCreate(
                collection_id=collection.collection_id,
                name=EMBEDDING_MODEL_NAME,
                embedding_dimension=embedding_dim,
            ),
        )
        sample_ids = sample_resolver.create_many(
            session=session,
            samples=[
                SampleCreate(collection_id=collection.collection_id) for _ in range(num_samples)
            ],
        )
        embeddings = _generate_embeddings(
            num_samples=num_samples, embedding_dim=embedding_dim, seed=seed
        )
        for batch in batching.batched(
            items=zip(sample_ids, embeddings), batch_size=INSERT_BATCH_SIZE
        ):
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


def _generate_embeddings(num_samples: int, embedding_dim: int, seed: int) -> NDArray[np.float32]:
    """Generate deterministic random float32 embeddings of shape (num_samples, embedding_dim)."""
    rng = np.random.default_rng(seed)
    return rng.random((num_samples, embedding_dim), dtype=np.float32)


def _run_phase(collection_id: UUID, embedding_model_id: UUID, expected_count: int) -> float:
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

    # A phase that silently returned nothing would look fast, so check the result size.
    if not len(x_values) == len(y_values) == len(sample_ids) == expected_count:
        raise ValueError(
            f"Expected {expected_count} points, got "
            f"x={len(x_values)} y={len(y_values)} sample_ids={len(sample_ids)}."
        )
    return elapsed


def _print_report(num_samples: int, cold_seconds: float, warm_seconds: float) -> None:
    """Print a compact, copy-pasteable results block."""
    speedup = cold_seconds / warm_seconds if warm_seconds > 0 else float("inf")
    print("")
    print("2D embedding benchmark")
    print(f"  backend=duckdb num_samples={num_samples}")
    print(f"  cold  time={cold_seconds:8.3f}s  (projection-dominated)")
    print(f"  warm  time={warm_seconds:8.3f}s  ({speedup:.1f}x faster than cold)")


if __name__ == "__main__":
    main()
