"""Benchmark: annotation query performance with and without DB indexes.

Inserts 10,000 annotations (10 per image, 1,000 images) and measures the
wall-clock time of get_all() filtered by collection_id and annotation_label_id.
Each query is executed 5 times; the median is reported.

The test does NOT assert a specific speedup ratio because in-memory DuckDB
already applies its own optimisations regardless of SQLModel index declarations.
Instead it documents baseline timings and prints them for human review.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Generator
from uuid import UUID

import pytest
from sqlmodel import Session, SQLModel, create_engine

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import (
    create_annotation_label,
    create_collection,
    create_image,
)

N_IMAGES = 1_000
ANNOTATIONS_PER_IMAGE = 10
QUERY_RUNS = 5


@pytest.fixture
def benchmark_db() -> Generator[Session, None, None]:
    """In-memory DuckDB session used for the benchmark."""
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def benchmark_data(benchmark_db: Session) -> tuple[UUID, UUID]:
    """Insert 10,000 annotations (10 per image x 1,000 images) and return IDs.

    Returns:
        A tuple of (collection_id, annotation_label_id) for use in queries.
    """
    session = benchmark_db

    collection = create_collection(session=session)
    label = create_annotation_label(
        session=session,
        dataset_id=collection.collection_id,
        label_name="benchmark_label",
    )

    # Build all AnnotationCreate objects upfront for efficient bulk insert.
    batch: list[AnnotationCreate] = []
    for i in range(N_IMAGES):
        image = create_image(
            session=session,
            collection_id=collection.collection_id,
            file_path_abs=f"/bench/image_{i:05d}.jpg",
        )
        for _ in range(ANNOTATIONS_PER_IMAGE):
            batch.append(
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=label.annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=0,
                    y=0,
                    width=100,
                    height=100,
                )
            )

    annotation_resolver.create_many(
        session=session,
        parent_collection_id=collection.collection_id,
        annotations=batch,
    )

    return collection.collection_id, label.annotation_label_id


def _median_query_time(session: Session, filters: AnnotationsFilter) -> float:
    """Run the filtered get_all query QUERY_RUNS times and return the median seconds."""
    times: list[float] = []
    for _ in range(QUERY_RUNS):
        start = time.perf_counter()
        annotation_resolver.get_all(session=session, filters=filters)
        times.append(time.perf_counter() - start)
    return statistics.median(times)


def test_query_by_collection_id(
    benchmark_db: Session,
    benchmark_data: tuple[UUID, UUID],
) -> None:
    """Benchmark: get_all filtered by collection_id."""
    collection_id, _ = benchmark_data

    filters = AnnotationsFilter(collection_ids=[collection_id])
    median_s = _median_query_time(session=benchmark_db, filters=filters)

    print(
        f"\n[benchmark] collection_id filter — median over {QUERY_RUNS} runs: "
        f"{median_s * 1000:.1f} ms"
    )
    # Sanity check: query must complete in a reasonable time.
    assert median_s < 60, f"Query took too long: {median_s:.1f} s"


def test_query_by_annotation_label_id(
    benchmark_db: Session,
    benchmark_data: tuple[UUID, UUID],
) -> None:
    """Benchmark: get_all filtered by annotation_label_id."""
    _, annotation_label_id = benchmark_data

    filters = AnnotationsFilter(annotation_label_ids=[annotation_label_id])
    median_s = _median_query_time(session=benchmark_db, filters=filters)

    print(
        f"\n[benchmark] annotation_label_id filter — median over {QUERY_RUNS} runs: "
        f"{median_s * 1000:.1f} ms"
    )
    # Sanity check: query must complete in a reasonable time.
    assert median_s < 60, f"Query took too long: {median_s:.1f} s"
