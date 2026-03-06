"""Benchmark tests for annotation query performance with and without database indexes.

This module measures the query time for annotation filtering operations to validate
that index=True on annotation_label_id and parent_sample_id provides acceptable
performance at scale.
"""

from __future__ import annotations

import statistics
import time
from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.models.annotation.annotation_base import AnnotationCreate, AnnotationType
from lightly_studio.resolvers import annotation_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from tests.helpers_resolvers import create_annotation_label, create_collection, create_image

N_IMAGES = 1_000
N_ANNOTATIONS_PER_IMAGE = 10
N_REPETITIONS = 5

# Maximum acceptable median query time in seconds.  This is intentionally generous
# to avoid flaky test failures on slow CI runners while still catching catastrophic
# regressions (e.g. full-table-scan at 1 M rows).
MAX_MEDIAN_SECONDS = 5.0


@pytest.fixture
def benchmark_data(
    test_db: Session,
) -> tuple[Session, UUID, UUID]:
    """Populate the database with N_IMAGES images and N_ANNOTATIONS_PER_IMAGE annotations each.

    Returns:
        A tuple of (session, annotation_collection_id, annotation_label_id).
        annotation_collection_id is the collection that the annotation *samples* belong to
        (a child collection of the parent image collection), which is what
        AnnotationsFilter.collection_ids filters on.
    """
    collection = create_collection(session=test_db)
    parent_collection_id: UUID = collection.collection_id

    label = create_annotation_label(
        session=test_db,
        dataset_id=parent_collection_id,
        label_name="benchmark_label",
    )
    annotation_label_id: UUID = label.annotation_label_id

    annotations_batch: list[AnnotationCreate] = []
    for i in range(N_IMAGES):
        image = create_image(
            session=test_db,
            collection_id=parent_collection_id,
            file_path_abs=f"/bench/image_{i:05d}.jpg",
        )
        for _ in range(N_ANNOTATIONS_PER_IMAGE):
            annotations_batch.append(
                AnnotationCreate(
                    parent_sample_id=image.sample_id,
                    annotation_label_id=annotation_label_id,
                    annotation_type=AnnotationType.OBJECT_DETECTION,
                    x=10,
                    y=10,
                    width=20,
                    height=20,
                )
            )

    ann_ids = annotation_resolver.create_many(
        session=test_db,
        parent_collection_id=parent_collection_id,
        annotations=annotations_batch,
    )

    # The annotation *samples* live in an auto-created child collection.
    # Retrieve that collection ID via the first annotation's sample.
    first_annotation = annotation_resolver.get_by_id(session=test_db, annotation_id=ann_ids[0])
    assert first_annotation is not None
    annotation_collection_id: UUID = first_annotation.sample.collection_id

    return test_db, annotation_collection_id, annotation_label_id


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
