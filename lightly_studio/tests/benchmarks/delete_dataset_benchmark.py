"""Delete-dataset benchmark (LIG-9899 / LIG-9915).

Times ``dataset_resolver.delete_dataset`` and reports wall-clock time and peak Python allocation.
``delete_dataset`` is enterprise-only, so this runs against PostgreSQL. The delete runs server-side
via subquery-scoped ``DELETE``s in a single transaction, so peak Python allocation should stay low
(a few MiB) regardless of dataset size — that is the key signal that no rows are materialized in
Python.

Two modes, run from the ``lightly_studio`` directory:

Generate a synthetic dataset of N images with embeddings, then delete it::

    make start-postgres
    uv run tests/benchmarks/delete_dataset_benchmark.py --generate 250000
    make stop-postgres

Delete an existing root collection by name (e.g. the COCO demo on an enterprise database, which
also exercises the annotation/video/evaluation delete paths)::

    LIGHTLY_STUDIO_DATABASE_URL=<postgres-url> \
        uv run tests/benchmarks/delete_dataset_benchmark.py --collection-name "coco"

WARNING: ``--collection-name`` is destructive — it permanently deletes the named collection and all
its data from the configured database. Use it only against a database you are willing to mutate
(e.g. a throwaway copy), not a database whose data you want to keep.

``--generate`` uses ``$LIGHTLY_STUDIO_DATABASE_URL`` if set (otherwise the default dev URL) and
recreates the database; ``--collection-name`` uses the configured database as-is.
"""

from __future__ import annotations

import argparse
import os
import time
import tracemalloc
from dataclasses import dataclass
from uuid import UUID

import numpy as np
from tqdm import tqdm

from lightly_studio import db_manager
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.embedding_model import EmbeddingModelCreate
from lightly_studio.models.image import ImageCreate
from lightly_studio.models.sample_embedding import SampleEmbeddingCreate
from lightly_studio.resolvers import (
    collection_resolver,
    dataset_resolver,
    embedding_model_resolver,
    image_resolver,
    sample_embedding_resolver,
)

_BYTES_PER_MIB = 1024 * 1024
DEFAULT_EMBEDDING_DIM = 512
DEFAULT_BATCH_SIZE = 5_000
DEFAULT_SEED = 0
DEFAULT_DATASET_NAME = "delete_dataset_benchmark"
DEFAULT_EMBEDDING_MODEL_NAME = "benchmark_embeddings"
DEFAULT_POSTGRES_URL = "postgresql://lightly:lightly@localhost:5433/lightly_studio"


@dataclass(frozen=True)
class GenerationConfig:
    """Configuration for generating the synthetic source dataset."""

    num_images: int
    embedding_dim: int
    batch_size: int
    seed: int


@dataclass(frozen=True)
class DeleteResult:
    """Wall-clock time and peak Python allocation for the delete."""

    wall_seconds: float
    peak_mib: float


def main() -> None:
    """Generate or locate a dataset, delete it, and print a report."""
    args = _parse_args()
    num_images: int | None = None
    source_label: str | None = None
    setup_seconds = 0.0

    if args.collection_name is not None:
        db_manager.connect()  # use the configured database as-is.
        source_label = args.collection_name
        print(f"WARNING: permanently deleting collection {source_label!r} from the database.")
        dataset_id = _resolve_dataset_id(name=args.collection_name)
    else:
        _connect_fresh_postgres()
        config = GenerationConfig(
            num_images=args.generate,
            embedding_dim=args.embedding_dim,
            batch_size=args.batch_size,
            seed=args.seed,
        )
        started = time.perf_counter()
        dataset_id = _generate_dataset(config=config)
        setup_seconds = time.perf_counter() - started
        num_images = config.num_images

    try:
        result = _run_delete(dataset_id=dataset_id)
    finally:
        db_manager.close()

    _print_report(
        num_images=num_images,
        source_label=source_label,
        setup_seconds=setup_seconds,
        result=result,
    )


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--generate",
        type=int,
        metavar="N",
        help="Generate N images with embeddings, then delete them.",
    )
    source.add_argument(
        "--collection-name",
        help="Permanently delete an existing root collection by name instead (destructive).",
    )
    parser.add_argument("--embedding-dim", type=int, default=DEFAULT_EMBEDDING_DIM)
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def _connect_fresh_postgres() -> None:
    """Connect to a fresh PostgreSQL database, recreating it."""
    db_manager.close()
    url = os.environ.get("LIGHTLY_STUDIO_DATABASE_URL", DEFAULT_POSTGRES_URL)
    db_manager.connect(db_url=url, cleanup_existing=True)


def _resolve_dataset_id(name: str) -> UUID:
    """Return the dataset id of the existing root collection with the given name."""
    with db_manager.session() as session:
        collection_id = collection_resolver.get_by_name(
            session=session, name=name, parent_collection_id=None
        )
        if collection_id is None:
            raise SystemExit(f"No root collection named {name!r}.")
        collection = collection_resolver.get_by_id(session=session, collection_id=collection_id)
        assert collection is not None
        return collection.dataset_id


def _generate_dataset(config: GenerationConfig) -> UUID:
    """Create a collection of ``num_images`` images with embeddings; return its dataset id."""
    rng = np.random.default_rng(config.seed)
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
        with tqdm(total=config.num_images, desc="Generating", unit="img") as progress:
            for start in range(0, config.num_images, config.batch_size):
                count = min(config.batch_size, config.num_images - start)
                sample_ids = image_resolver.create_many(
                    session=session,
                    collection_id=collection.collection_id,
                    samples=[
                        ImageCreate(
                            file_path_abs=f"/benchmark/{start + i}.png",
                            file_name=f"{start + i}.png",
                            width=640,
                            height=480,
                        )
                        for i in range(count)
                    ],
                )
                embeddings = rng.random((count, config.embedding_dim), dtype=np.float32)
                sample_embedding_resolver.create_many(
                    session=session,
                    sample_embeddings=[
                        SampleEmbeddingCreate(
                            sample_id=sample_id,
                            embedding_model_id=embedding_model.embedding_model_id,
                            embedding=embeddings[index],
                        )
                        for index, sample_id in enumerate(sample_ids)
                    ],
                )
                progress.update(count)
        return collection.dataset_id


def _run_delete(dataset_id: UUID) -> DeleteResult:
    """Delete the dataset, measuring time and peak Python allocation."""
    with db_manager.session() as session:
        tracemalloc.start()
        tracemalloc.reset_peak()
        started = time.perf_counter()
        dataset_resolver.delete_dataset(session=session, dataset_id=dataset_id)
        elapsed = time.perf_counter() - started
        peak_mib = tracemalloc.get_traced_memory()[1] / _BYTES_PER_MIB
        tracemalloc.stop()

    return DeleteResult(wall_seconds=elapsed, peak_mib=peak_mib)


def _print_report(
    num_images: int | None,
    source_label: str | None,
    setup_seconds: float,
    result: DeleteResult,
) -> None:
    """Print a compact, copy-pasteable results block."""
    print("")
    print("Delete-dataset benchmark")
    if num_images is not None:
        print(f"  generated num_images={num_images:,} setup_time={setup_seconds:.3f}s")
    if source_label is not None:
        print(f"  deleted collection={source_label!r}")
    print(f"  delete time={result.wall_seconds:.3f}s peak_python_mem={result.peak_mib:.1f} MiB")


if __name__ == "__main__":
    main()
