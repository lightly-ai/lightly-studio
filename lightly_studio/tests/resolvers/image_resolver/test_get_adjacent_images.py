from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import pytest
from sqlalchemy import event
from sqlmodel import Session

from lightly_studio.core.dataset_query.image_sample_field import ImageSampleField
from lightly_studio.core.dataset_query.order_by import (
    OrderByEvaluationMetricField,
    OrderByField,
    OrderByMetadataField,
)
from lightly_studio.models.image import ImageCreate
from lightly_studio.resolvers import image_resolver, metadata_resolver
from lightly_studio.resolvers.annotations.annotations_filter import AnnotationsFilter
from lightly_studio.resolvers.image_filter import ImageFilter
from lightly_studio.resolvers.sample_resolver.sample_filter import SampleFilter
from tests import helpers_resolvers
from tests.helpers_resolvers import AnnotationDetails
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    SampleMetricStub,
    create_run,
    create_sample_metrics,
)


@contextmanager
def _capture_sql(session: Session) -> Generator[list[tuple[str, Any]], None, None]:
    """Record every SQL statement (and its params) executed on the session's engine."""
    statements: list[tuple[str, Any]] = []
    bind = session.get_bind()

    def _before_cursor_execute(
        _conn: Any, _cursor: Any, statement: str, parameters: Any, _context: Any, _many: bool
    ) -> None:
        statements.append((statement, parameters))

    event.listen(bind, "before_cursor_execute", _before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(bind, "before_cursor_execute", _before_cursor_execute)


def _selects(statements: list[tuple[str, Any]]) -> list[str]:
    return [stmt for stmt, _ in statements if stmt.lstrip().upper().startswith("SELECT")]


def test_get_adjacent_images__orders_by_path(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id
    assert result.current_sample_position == 2
    assert result.total_count == 3


def test_get_adjacent_images__respects_sample_ids(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(sample_ids=[image_b.sample_id, image_c.sample_id])
        ),
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images__respects_annotation_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    dog_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="dog",
    )
    cat_label = helpers_resolvers.create_annotation_label(
        session=db_session,
        root_collection_id=collection_id,
        label_name="cat",
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_annotations(
        session=db_session,
        collection_id=collection_id,
        annotations=[
            AnnotationDetails(
                sample_id=image_a.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_b.sample_id,
                annotation_label_id=dog_label.annotation_label_id,
            ),
            AnnotationDetails(
                sample_id=image_c.sample_id,
                annotation_label_id=cat_label.annotation_label_id,
            ),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        filters=ImageFilter(
            sample_filter=SampleFilter(
                annotations_filter=AnnotationsFilter(
                    annotation_label_ids=[dog_label.annotation_label_id],
                ),
            )
        ),
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id is None
    assert result.current_sample_position == 2
    assert result.total_count == 2


def test_get_adjacent_images__with_similarity(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_a.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.0, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_b.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[0.5, 1.0],
    )
    helpers_resolvers.create_sample_embedding(
        session=db_session,
        sample_id=image_c.sample_id,
        embedding_model_id=embedding_model.embedding_model_id,
        embedding=[1.0, 1.0],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        text_embedding=[1.0, 1.0],
    )

    assert result is not None
    assert result.previous_sample_id is None
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_b.sample_id
    assert result.current_sample_position == 1
    assert result.total_count == 3


def test_get_adjacent_images__sort_by_file_name(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    # Insert in non-sorted order to verify sorting is applied
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    # Sorted order is a, b, c — so image_b's previous is a, next is c
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name)],
    )

    assert result is not None
    assert result.previous_sample_id == image_a.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_c.sample_id


def test_get_adjacent_images__sort_by_file_name_desc(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    # Insert in non-sorted order to verify sorting is applied
    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
    )

    # Descending: sorted order is c, b, a — so image_b's previous is c, next is a
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_b.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.file_name).desc()],
    )

    assert result is not None
    assert result.previous_sample_id == image_c.sample_id
    assert result.sample_id == image_b.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__sort_by_width_desc_with_duplicate_values(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_b = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/b.png",
        width=1920,
    )
    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/a.png",
        width=1920,
    )
    image_c = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection_id,
        file_path_abs="/images/c.png",
        width=1080,
    )

    # Both image_a and image_b have width=1920. The secondary tiebreaker is file_path_abs DESC
    # (matching the primary direction), so b.png comes before a.png.
    # Order: b.png (1920), a.png (1920), c.png (1080)
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_a.sample_id,
        collection_id=collection_id,
        order_by=[OrderByField(ImageSampleField.width).desc()],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_a.sample_id
    assert result.next_sample_id == image_c.sample_id


def test_get_adjacent_images__returns_none_when_sample_not_in_filter(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_1 = helpers_resolvers.create_collection(
        session=db_session, collection_name="collection_1"
    )

    image_a = helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/a.png",
    )
    helpers_resolvers.create_image(
        session=db_session,
        collection_id=collection.collection_id,
        file_path_abs="/images/b.png",
    )

    # Use a filter that includes only samples from collection_1,
    # which does not include image_a.sample_id
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_a.sample_id,
        collection_id=collection_1.collection_id,
    )

    assert result is None


def test_get_adjacent_images__sort_by_metadata_field(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    image_a = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/a.png"
    )
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so sorted sequence is b, c, a
    metadata_resolver.bulk_update_metadata(
        db_session,
        [
            (image_a.sample_id, {"score": 3}),
            (image_b.sample_id, {"score": 1}),
            (image_c.sample_id, {"score": 2}),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByMetadataField("score", cast_to_float=True)],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


def test_get_adjacent_images__sort_by_evaluation_metric(db_session: Session) -> None:
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    run = create_run(session=db_session, dataset_collection_id=collection_id)
    image_a = helpers_resolvers.create_image(session=db_session, collection_id=collection_id)
    image_b = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/b.png"
    )
    image_c = helpers_resolvers.create_image(
        session=db_session, collection_id=collection_id, file_path_abs="/images/c.png"
    )

    # score order: b(1) < c(2) < a(3), so sorted sequence is b, c, a
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(sample_id=image_a.sample_id, metrics={"score": 3.0}),
            SampleMetricStub(sample_id=image_b.sample_id, metrics={"score": 1.0}),
            SampleMetricStub(sample_id=image_c.sample_id, metrics={"score": 2.0}),
        ],
    )

    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=image_c.sample_id,
        collection_id=collection_id,
        order_by=[OrderByEvaluationMetricField("test_run", "score")],
    )

    assert result is not None
    assert result.previous_sample_id == image_b.sample_id
    assert result.sample_id == image_c.sample_id
    assert result.next_sample_id == image_a.sample_id


# ---------------------------------------------------------------------------------------
# Scalability / full-scan regression guards (LIG-9925).
#
# The previous implementation computed lag/lead/row_number window functions over the
# entire collection on every prev/next click, forcing a full sort + scan. These tests
# lock in the keyset (seek) rewrite so that pathology cannot silently return.
# ---------------------------------------------------------------------------------------


def test_get_adjacent_images__keyset_path_emits_no_window_functions(db_session: Session) -> None:
    """Default-sort adjacency must not use SQL window functions (the full-scan pattern)."""
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    images = [
        helpers_resolvers.create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/images/{i}.png"
        )
        for i in range(5)
    ]

    with _capture_sql(db_session) as statements:
        result = image_resolver.get_adjacent_images(
            session=db_session,
            sample_id=images[2].sample_id,
            collection_id=collection_id,
        )

    assert result is not None
    select_statements = _selects(statements)
    assert select_statements, "expected the resolver to execute SELECT statements"
    offending = [stmt for stmt in select_statements if "OVER (" in stmt.upper()]
    assert not offending, (
        "keyset adjacency must not emit window functions (OVER (...)); "
        f"found window SQL: {offending}"
    )


def test_get_adjacent_images__similarity_still_uses_window_fallback(db_session: Session) -> None:
    """Similarity search has no seekable sort key, so it keeps the window implementation."""
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    embedding_model = helpers_resolvers.create_embedding_model(
        session=db_session,
        collection_id=collection_id,
        embedding_model_name="embedding-for-adjacency",
        embedding_dimension=2,
    )
    images = []
    for i in range(3):
        image = helpers_resolvers.create_image(
            session=db_session, collection_id=collection_id, file_path_abs=f"/images/{i}.png"
        )
        helpers_resolvers.create_sample_embedding(
            session=db_session,
            sample_id=image.sample_id,
            embedding_model_id=embedding_model.embedding_model_id,
            embedding=[float(i), 1.0],
        )
        images.append(image)

    with _capture_sql(db_session) as statements:
        result = image_resolver.get_adjacent_images(
            session=db_session,
            sample_id=images[1].sample_id,
            collection_id=collection_id,
            text_embedding=[1.0, 1.0],
        )

    assert result is not None
    assert any("OVER (" in stmt.upper() for stmt in _selects(statements)), (
        "similarity adjacency is expected to fall back to the window implementation"
    )


def test_get_adjacent_images__correct_at_scale(db_session: Session) -> None:
    """Keyset prev/next/position/total stay correct as the collection grows."""
    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id

    count = 500
    # Insert in shuffled order to ensure ordering is driven by file_path_abs, not insertion.
    order = list(range(count))
    order = order[::2] + order[1::2]
    sample_ids = image_resolver.create_many(
        session=db_session,
        collection_id=collection_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/images/{i:04d}.png",
                file_name=f"{i:04d}.png",
                width=100,
                height=100,
            )
            for i in order
        ],
    )
    # Map sorted position -> sample_id. Paths sort lexicographically == numeric here.
    id_by_index = dict(zip(order, sample_ids))

    middle = count // 2
    result = image_resolver.get_adjacent_images(
        session=db_session,
        sample_id=id_by_index[middle],
        collection_id=collection_id,
    )
    assert result is not None
    assert result.previous_sample_id == id_by_index[middle - 1]
    assert result.next_sample_id == id_by_index[middle + 1]
    assert result.current_sample_position == middle + 1  # 1-based
    assert result.total_count == count

    # First element: no previous.
    first = image_resolver.get_adjacent_images(
        session=db_session, sample_id=id_by_index[0], collection_id=collection_id
    )
    assert first is not None
    assert first.previous_sample_id is None
    assert first.next_sample_id == id_by_index[1]
    assert first.current_sample_position == 1

    # Last element: no next.
    last = image_resolver.get_adjacent_images(
        session=db_session, sample_id=id_by_index[count - 1], collection_id=collection_id
    )
    assert last is not None
    assert last.previous_sample_id == id_by_index[count - 2]
    assert last.next_sample_id is None
    assert last.current_sample_position == count


def test_get_adjacent_images__seek_uses_index_on_postgres(db_session: Session) -> None:
    """On Postgres the prev/next seek must be index-supported, not a full sort/scan.

    Runs only under ``--postgres``; DuckDB is columnar and has no comparable range
    index, so the guarantee (and this assertion) is Postgres-specific.
    """
    bind = db_session.get_bind()
    if bind.dialect.name != "postgresql":
        pytest.skip("Index-scan plan guarantee is Postgres-specific")

    collection = helpers_resolvers.create_collection(session=db_session)
    collection_id = collection.collection_id
    sample_ids = image_resolver.create_many(
        session=db_session,
        collection_id=collection_id,
        samples=[
            ImageCreate(
                file_path_abs=f"/images/{i:04d}.png",
                file_name=f"{i:04d}.png",
                width=100,
                height=100,
            )
            for i in range(200)
        ],
    )

    with _capture_sql(db_session) as statements:
        image_resolver.get_adjacent_images(
            session=db_session,
            sample_id=sample_ids[100],
            collection_id=collection_id,
        )

    seek_statements = [
        (stmt, params)
        for stmt, params in statements
        if "ORDER BY" in stmt.upper() and "LIMIT" in stmt.upper()
    ]
    assert seek_statements, "expected prev/next seek statements with ORDER BY ... LIMIT"

    connection = db_session.connection()
    # Force the planner to prefer indexes so a tiny test table still reveals whether the
    # seek query *can* use the composite index (small tables otherwise favour Seq Scan).
    connection.exec_driver_sql("SET enable_seqscan = off")
    for stmt, params in seek_statements:
        plan_rows = connection.exec_driver_sql("EXPLAIN " + stmt, params).fetchall()
        plan = "\n".join(str(row[0]) for row in plan_rows)
        assert "ix_image_file_path_abs_sample_id" in plan, (
            f"seek query should use the composite index; plan was:\n{plan}"
        )
