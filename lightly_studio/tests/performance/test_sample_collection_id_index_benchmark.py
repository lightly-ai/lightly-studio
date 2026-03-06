"""Benchmark for sample_resolver.get_filtered_samples() filtered by collection_id.

This test measures the wall-clock time of querying samples filtered by
collection_id, demonstrating the performance impact of adding an index
on SampleTable.collection_id.
"""

import statistics
import time
from collections.abc import Generator

import pytest
from sqlmodel import Session

from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import collection_resolver, image_resolver, sample_resolver
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter

_IMAGES_PER_COLLECTION = 2_000
_NUM_COLLECTIONS = 2
_NUM_RUNS = 5


@pytest.fixture
def benchmark_session() -> Generator[Session, None, None]:
    """Yield an in-memory DuckDB session pre-populated for benchmarking."""
    engine = DatabaseEngine("duckdb:///:memory:", single_threaded=True)
    with engine.session() as session:
        yield session


def _populate_session(session: Session) -> list[str]:
    """Insert _NUM_COLLECTIONS collections each with _IMAGES_PER_COLLECTION images.

    Args:
        session: The database session to populate.

    Returns:
        List of collection_id strings for all created collections.
    """
    collection_ids = []
    for i in range(_NUM_COLLECTIONS):
        collection = collection_resolver.create(
            session,
            CollectionCreate(
                name=f"benchmark_collection_{i}",
                sample_type=SampleType.IMAGE,
            ),
        )
        image_resolver.create_many(
            session=session,
            collection_id=collection.collection_id,
            samples=[
                ImageCreate(
                    file_path_abs=f"/benchmark/col{i}/img_{j}.jpg",
                    file_name=f"img_{j}.jpg",
                    width=640,
                    height=480,
                )
                for j in range(_IMAGES_PER_COLLECTION)
            ],
        )
        collection_ids.append(collection.collection_id)
    return collection_ids


def test_get_filtered_samples_by_collection_id(benchmark_session: Session) -> None:
    """Benchmark get_filtered_samples() filtered by collection_id.

    Creates _NUM_COLLECTIONS x _IMAGES_PER_COLLECTION rows in SampleTable,
    then measures the wall-clock time to query one collection's samples.
    Runs _NUM_RUNS iterations and reports the median latency.
    """
    collection_ids = _populate_session(benchmark_session)
    target_collection_id = collection_ids[0]

    # Warm-up run (not counted)
    warm_up = sample_resolver.get_filtered_samples(
        session=benchmark_session,
        filters=SampleFilter(collection_id=target_collection_id),
    )
    assert warm_up.total_count == _IMAGES_PER_COLLECTION

    # Timed runs
    timings: list[float] = []
    for _ in range(_NUM_RUNS):
        start = time.perf_counter()
        result = sample_resolver.get_filtered_samples(
            session=benchmark_session,
            filters=SampleFilter(collection_id=target_collection_id),
        )
        elapsed = time.perf_counter() - start
        timings.append(elapsed)
        assert result.total_count == _IMAGES_PER_COLLECTION

    median_ms = statistics.median(timings) * 1_000
    min_ms = min(timings) * 1_000
    max_ms = max(timings) * 1_000
    print(
        f"\nget_filtered_samples() by collection_id — "
        f"{_NUM_COLLECTIONS} collections x {_IMAGES_PER_COLLECTION} images each "
        f"({_NUM_COLLECTIONS * _IMAGES_PER_COLLECTION} total rows)\n"
        f"  Runs (ms): {[f'{t * 1_000:.2f}' for t in timings]}\n"
        f"  Min={min_ms:.2f} ms  Median={median_ms:.2f} ms  Max={max_ms:.2f} ms"
    )
