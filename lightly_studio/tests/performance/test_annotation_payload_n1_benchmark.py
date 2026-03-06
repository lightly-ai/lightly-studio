"""Benchmark for N+1 query detection in annotation payload resolver.

This test measures the number of SELECT statements issued by SQLAlchemy when
calling ``annotation_resolver.get_all_with_payload`` for a page of 100
annotations.  It serves both as documentation of the historical N+1 problem
and as a regression guard that fails if the query count grows back.

Before the fix the resolver issued up to ~312 extra SELECTs for a page of 100
annotations with 10 distinct labels:
  - 1   SELECT for annotation rows
  - 1   SELECT for the total-count subquery
  - 10  SELECTs for unique annotation_label rows   (lazy "select")
  - 100 SELECTs for object_detection_details       (lazy "select")
  - 100 SELECTs for annotation sample rows         (lazy "select")
  - 100 SELECTs for sample.tags                    (lazy "select")

After adding eager-loading options in ``_build_base_query`` the number of
additional round-trips drops to a small constant regardless of page size.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

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

_N_IMAGES = 100
_N_LABELS = 10


def _setup_db() -> tuple[Session, UUID]:
    """Create an in-memory DuckDB session with 100 annotated images.

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

    # Create 10 distinct labels
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

    # Create 100 images
    image_ids = image_resolver.create_many(
        session=session,
        collection_id=parent_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/bench/image_{i:03d}.png",
                file_name=f"image_{i:03d}.png",
                width=640,
                height=480,
            )
            for i in range(_N_IMAGES)
        ],
    )

    # Create one object-detection annotation per image, cycling through labels
    annotations_input = [
        AnnotationCreate(
            parent_sample_id=img_id,
            annotation_label_id=labels[i % _N_LABELS].annotation_label_id,
            annotation_type=AnnotationType.OBJECT_DETECTION,
            x=10,
            y=10,
            width=50,
            height=50,
        )
        for i, img_id in enumerate(image_ids)
    ]
    annotation_ids = annotation_resolver.create_many(
        session=session,
        parent_collection_id=parent_id,
        annotations=annotations_input,
    )

    # Derive the annotation child collection id from one of the created
    # annotations.  Each annotation's sample.collection_id points to the
    # child annotation collection, which is what get_all_with_payload expects.
    first_annotation = annotation_resolver.get_by_id(
        session=session, annotation_id=annotation_ids[0]
    )
    assert first_annotation is not None
    annotation_collection_id = first_annotation.sample.collection_id

    return session, annotation_collection_id


def _count_selects(session: Session, annotation_collection_id: UUID) -> int:
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
    try:
        annotation_resolver.get_all_with_payload(
            session=session,
            collection_id=annotation_collection_id,
        )
    finally:
        event.remove(engine, "before_cursor_execute", _on_execute)

    return select_count


@pytest.fixture(scope="module")
def bench_session() -> tuple[Session, UUID]:
    """Module-scoped fixture: build the benchmark DB once for all tests."""
    return _setup_db()


def test_get_all_with_payload_select_count(
    bench_session: tuple[Session, UUID],
) -> None:
    """Verify that eager loading keeps the SELECT count to a small constant.

    With lazy loading (before the fix) a page of 100 annotations with 10
    distinct labels would produce at minimum ~312 SELECT statements.

    After the fix (joinedload/selectinload) the extra relationships are
    resolved in at most a handful of additional queries regardless of page
    size.  We assert an upper bound of 20 to leave headroom for internal
    framework queries while still catching regressions.
    """
    session, annotation_collection_id = bench_session
    select_count = _count_selects(session, annotation_collection_id)

    # With eager loading the count must stay well below the N+1 worst case.
    assert select_count <= 20, (
        f"Too many SELECT statements ({select_count}).  "
        "Possible N+1 regression in get_all_with_payload."
    )
