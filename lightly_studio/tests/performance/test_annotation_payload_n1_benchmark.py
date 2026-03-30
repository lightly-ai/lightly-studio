"""Benchmark for N+1 query detection in annotation payload resolver.

This test measures the number of SELECT statements issued by SQLAlchemy when
calling ``annotation_resolver.get_all_with_payload`` for a page of
``_PAGE_SIZE`` annotations drawn from a dataset of ``_N_IMAGES`` images each
carrying ``_N_ANNOTATIONS_PER_IMAGE`` annotations
(``_N_IMAGES * _N_ANNOTATIONS_PER_IMAGE`` annotations total).

It serves both as documentation of the historical N+1 problem and as a
regression guard that fails if the query count grows back.

Before the fix the resolver issued up to ~312 extra SELECTs for a page of
100 annotations with 10 distinct labels:
  - 1   SELECT for annotation rows
  - 1   SELECT for the total-count subquery
  - 10  SELECTs for unique annotation_label rows  (lazy "select")
  - 100 SELECTs for object_detection_details      (lazy "select")
  - 100 SELECTs for annotation sample rows        (lazy "select")
  - 100 SELECTs for sample.tags                   (lazy "select")

After adding eager-loading options in ``_build_base_query`` the number of
additional round-trips drops to a small constant regardless of page size.

DB setup inserts images and annotations in batches of ``_BATCH_SIZE`` rows to
keep memory usage reasonable and avoid handing very large lists to
``bulk_save_objects`` in a single call.
"""

from __future__ import annotations

import math
import time
from collections.abc import Iterator
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

from lightly_studio.api.routes.api.validators import Paginated
from lightly_studio.models.annotation.annotation_base import (
    AnnotationCreate,
    AnnotationType,
)
from lightly_studio.models.annotation_label import AnnotationLabelCreate
from lightly_studio.models.collection import CollectionCreate, SampleType
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import (
    annotation_label_resolver,
    annotation_resolver,
    collection_resolver,
    image_resolver,
)

_N_IMAGES = 10_000
_N_ANNOTATIONS_PER_IMAGE = 10
_N_LABELS = 10
_BATCH_SIZE = 5_000
_PAGE_SIZE = 100


def _batched(items: list[Any], batch_size: int) -> Iterator[list[Any]]:
    """Yield successive slices of *items* of length *batch_size*."""
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def _setup_db() -> tuple[Session, UUID]:
    """Create an in-memory DuckDB session with the benchmark dataset.

    Dataset:
        - ``_N_IMAGES`` images created in batches of ``_BATCH_SIZE``
        - ``_N_ANNOTATIONS_PER_IMAGE`` object-detection annotations per image,
          cycling through ``_N_LABELS`` distinct labels, created in batches of
          ``_BATCH_SIZE``

    Returns:
        A tuple of ``(session, annotation_collection_id)`` where
        ``annotation_collection_id`` is the child annotation collection that
        ``get_all_with_payload`` expects as input.
    """
    engine = create_engine("duckdb:///:memory:")
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    # Parent image collection
    parent_collection = collection_resolver.create(
        session=session,
        collection=CollectionCreate(name="bench_images", sample_type=SampleType.IMAGE),
    )
    parent_id = parent_collection.collection_id

    # Create _N_LABELS distinct labels (small, no batching needed)
    labels = [
        annotation_label_resolver.create(
            session=session,
            label=AnnotationLabelCreate(
                dataset_id=parent_id,
                annotation_label_name=f"label_{i}",
            ),
        )
        for i in range(_N_LABELS)
    ]
    label_ids = [lbl.annotation_label_id for lbl in labels]

    # ------------------------------------------------------------------
    # Create _N_IMAGES images in batches of _BATCH_SIZE
    # ------------------------------------------------------------------
    all_image_ids: list[UUID] = []
    n_image_batches = math.ceil(_N_IMAGES / _BATCH_SIZE)
    for batch_idx in range(n_image_batches):
        start = batch_idx * _BATCH_SIZE
        end = min(start + _BATCH_SIZE, _N_IMAGES)
        batch_ids = image_resolver.create_many(
            session=session,
            collection_id=parent_id,
            samples=[
                ImageCreate(
                    file_path_abs=f"/bench/image_{i:05d}.png",
                    file_name=f"image_{i:05d}.png",
                    width=640,
                    height=480,
                )
                for i in range(start, end)
            ],
        )
        all_image_ids.extend(batch_ids)

    # ------------------------------------------------------------------
    # Build the full annotations list and insert in batches.
    # Each image receives _N_ANNOTATIONS_PER_IMAGE annotations.  The
    # label index is computed as a flat sequence index modulo _N_LABELS
    # so that labels are spread evenly across both images and per-image
    # annotation slots rather than resetting to label_0 for every image.
    # ------------------------------------------------------------------
    all_annotations = [
        AnnotationCreate(
            parent_sample_id=img_id,
            annotation_label_id=label_ids[
                (img_idx * _N_ANNOTATIONS_PER_IMAGE + ann_idx) % _N_LABELS
            ],
            annotation_type=AnnotationType.OBJECT_DETECTION,
            x=10 + ann_idx,
            y=10 + ann_idx,
            width=50,
            height=50,
        )
        for img_idx, img_id in enumerate(all_image_ids)
        for ann_idx in range(_N_ANNOTATIONS_PER_IMAGE)
    ]

    annotation_collection_id: UUID | None = None
    for batch in _batched(all_annotations, _BATCH_SIZE):
        batch_ids = annotation_resolver.create_many(
            session=session,
            parent_collection_id=parent_id,
            annotations=batch,
        )
        if annotation_collection_id is None:
            # Resolve the child annotation collection id once from the first batch.
            first_annotation = annotation_resolver.get_by_id(
                session=session, annotation_id=batch_ids[0]
            )
            assert first_annotation is not None
            annotation_collection_id = first_annotation.sample.collection_id

    assert annotation_collection_id is not None
    return session, annotation_collection_id


def _count_selects(
    session: Session,
    annotation_collection_id: UUID,
    pagination: Paginated,
) -> int:
    """Run ``get_all_with_payload`` and return the number of SELECT statements.

    Uses SQLAlchemy's ``before_cursor_execute`` engine event to count every
    statement that begins with ``SELECT`` (case-insensitive).
    """
    engine = session.get_bind()
    select_count = 0

    def _on_execute(
        _conn: Any,
        _cursor: Any,
        statement: str,
        _parameters: Any,
        _context: Any,
        _executemany: bool,
    ) -> None:
        nonlocal select_count
        if statement.lstrip().upper().startswith("SELECT"):
            select_count += 1

    event.listen(engine, "before_cursor_execute", _on_execute)
    t0 = time.perf_counter()
    try:
        annotation_resolver.get_all_with_payload(
            session=session,
            collection_id=annotation_collection_id,
            pagination=pagination,
        )
    finally:
        elapsed = time.perf_counter() - t0
        event.remove(engine, "before_cursor_execute", _on_execute)

    print(
        f"\nget_all_with_payload(page={pagination.limit}) "
        f"took {elapsed:.3f}s with {select_count} SELECT(s)"
    )
    return select_count


@pytest.fixture(scope="module")
def bench_session() -> tuple[Session, UUID]:
    """Module-scoped fixture: build the benchmark DB once for all tests."""
    return _setup_db()


@pytest.mark.timeout(600)
def test_get_all_with_payload_select_count(
    bench_session: tuple[Session, UUID],
) -> None:
    """Verify that eager loading keeps the SELECT count to a small constant.

    Dataset: ``_N_IMAGES`` images with ``_N_ANNOTATIONS_PER_IMAGE`` annotations
    each, ``_N_LABELS`` distinct labels.

    With lazy loading (before the fix) a page of ``_PAGE_SIZE`` annotations
    with 10 distinct labels would produce ~312 SELECT statements.

    After the fix (joinedload/selectinload) the extra relationships are
    resolved in at most a handful of additional queries regardless of page
    size.  We assert an upper bound of 20 to leave headroom for internal
    framework queries while still catching regressions.
    """
    session, annotation_collection_id = bench_session
    pagination = Paginated(limit=_PAGE_SIZE, offset=0)
    select_count = _count_selects(session, annotation_collection_id, pagination)

    # With eager loading the count must stay well below the N+1 worst case.
    assert select_count <= 20, (
        f"Too many SELECT statements ({select_count}).  "
        "Possible N+1 regression in get_all_with_payload."
    )
