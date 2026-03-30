"""Benchmark tests for annotation query performance with and without database indexes.

This module measures the query time for annotation filtering operations to validate
that index=True on annotation_label_id and parent_sample_id provides acceptable
performance at scale.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Generator
from uuid import UUID

import pytest
from sqlmodel import Session, SQLModel, create_engine

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import annotation_resolver, image_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import create_annotation_label, create_collection

N_IMAGES = 100_000
N_ANNOTATIONS_PER_IMAGE = 1
N_REPETITIONS = 5

# Maximum acceptable median query time in seconds.  This is intentionally generous
# to avoid flaky test failures on slow CI runners while still catching catastrophic
# regressions (e.g. full-table-scan at 1 M rows).
MAX_MEDIAN_SECONDS = 5.0


@pytest.fixture(scope="module")
def bench_db() -> Generator[Session, None, None]:
    """Module-scoped in-memory DuckDB session shared by all benchmark tests.

    Using module scope avoids repeating the expensive data-insertion setup for
    every test function in this file.
    """
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(scope="module")
def benchmark_data(
    bench_db: Session,
) -> tuple[Session, UUID, UUID]:
    """Populate the database with N_IMAGES images and N_ANNOTATIONS_PER_IMAGE annotations each.

    Images are created in a single bulk call to keep fixture setup time acceptable at
    100 k scale.

    Returns:
        A tuple of (session, annotation_collection_id, annotation_label_id).
        annotation_collection_id is the collection that the annotation *samples* belong to
        (a child collection of the parent image collection), which is what
        AnnotationsFilter.collection_ids filters on.
    """
    collection = create_collection(session=bench_db)
    parent_collection_id: UUID = collection.collection_id

    label = create_annotation_label(
        session=bench_db,
        dataset_id=parent_collection_id,
        label_name="benchmark_label",
    )
    annotation_label_id: UUID = label.annotation_label_id

    # Bulk-create all images in a single database round-trip.
    image_sample_ids = image_resolver.create_many(
        session=bench_db,
        collection_id=parent_collection_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/bench/image_{i:06d}.jpg",
                file_name=f"image_{i:06d}.jpg",
                width=1920,
                height=1080,
            )
            for i in range(N_IMAGES)
        ],
    )

    annotations_batch: list[AnnotationCreate] = [
        AnnotationCreate(
            parent_sample_id=sample_id,
            annotation_label_id=annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            x=10,
            y=10,
            width=20,
            height=20,
        )
        for sample_id in image_sample_ids
        for _ in range(N_ANNOTATIONS_PER_IMAGE)
    ]

    ann_ids = annotation_resolver.create_many(
        session=bench_db,
        parent_collection_id=parent_collection_id,
        annotations=annotations_batch,
    )

    # The annotation *samples* live in an auto-created child collection.
    # Retrieve that collection ID via the first annotation's sample.
    first_annotation = annotation_resolver.get_by_id(session=bench_db, annotation_id=ann_ids[0])
    assert first_annotation is not None
    annotation_collection_id: UUID = first_annotation.sample.collection_id

    return bench_db, annotation_collection_id, annotation_label_id


def _measure_query(
    session: Session,
    filters: AnnotationsFilter,
    n_reps: int = N_REPETITIONS,
) -> float:
    """Run the filtered get_all query *n_reps* times and return the median wall-clock time."""
    times: list[float] = []
    for _ in range(n_reps):
        start = time.perf_counter()
        result = annotation_resolver.get_all(session=session, filters=filters)
        elapsed = time.perf_counter() - start
        times.append(elapsed)
        # Sanity-check: the query must return some results.
        assert result.total_count > 0, "Expected annotations but got none."

    return statistics.median(times)


def test_get_all_filtered_by_collection_id(
    benchmark_data: tuple[Session, UUID, UUID],
) -> None:
    """Benchmark get_all() filtered by collection_id.

    Inserts N_IMAGES * N_ANNOTATIONS_PER_IMAGE annotations and measures the median
    query time across N_REPETITIONS runs.  The test fails if the median exceeds
    MAX_MEDIAN_SECONDS, which would indicate a catastrophic regression.
    """
    session, collection_id, _ = benchmark_data
    filters = AnnotationsFilter(collection_ids=[collection_id])

    median_time = _measure_query(session, filters)
    print(
        f"\n[benchmark] collection_id filter - "
        f"median over {N_REPETITIONS} runs: {median_time:.4f}s "
        f"(limit: {MAX_MEDIAN_SECONDS}s)"
    )
    assert median_time < MAX_MEDIAN_SECONDS, (
        f"Query by collection_id took {median_time:.4f}s (limit: {MAX_MEDIAN_SECONDS}s). "
        "Possible missing index on parent_sample_id or annotation_label_id."
    )


def test_get_all_filtered_by_annotation_label_id(
    benchmark_data: tuple[Session, UUID, UUID],
) -> None:
    """Benchmark get_all() filtered by annotation_label_id.

    Inserts N_IMAGES * N_ANNOTATIONS_PER_IMAGE annotations and measures the median
    query time across N_REPETITIONS runs.  The test fails if the median exceeds
    MAX_MEDIAN_SECONDS.
    """
    session, collection_id, annotation_label_id = benchmark_data
    filters = AnnotationsFilter(
        collection_ids=[collection_id],
        annotation_label_ids=[annotation_label_id],
    )

    median_time = _measure_query(session, filters)
    print(
        f"\n[benchmark] annotation_label_id filter - "
        f"median over {N_REPETITIONS} runs: {median_time:.4f}s "
        f"(limit: {MAX_MEDIAN_SECONDS}s)"
    )
    assert median_time < MAX_MEDIAN_SECONDS, (
        f"Query by annotation_label_id took {median_time:.4f}s (limit: {MAX_MEDIAN_SECONDS}s). "
        "Possible missing index on annotation_label_id."
    )
