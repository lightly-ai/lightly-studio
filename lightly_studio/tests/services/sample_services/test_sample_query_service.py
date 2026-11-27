from __future__ import annotations

from uuid import UUID

import pytest
from sqlmodel import Session

from lightly_studio.core.dataset_query.dataset_query import DatasetQuery
from lightly_studio.core.dataset_query.order_by import OrderByMetadataField
from lightly_studio.errors import QueryExprError
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import (
    EvaluationMetricSortKey,
    SampleInclude,
    SampleQueryRequest,
    SortKey,
)
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.resolvers import metadata_resolver, tag_resolver
from lightly_studio.services.sample_services import sample_query_cursor, sample_query_service
from tests.helpers_resolvers import create_collection, create_image, create_tag
from tests.resolvers.evaluation_sample_metric_resolver.helpers import (
    SampleMetricStub,
    create_run,
    create_sample_metrics,
)

WIDTH = FieldRef(table="image", name="width")
FILE_NAME = FieldRef(table="image", name="file_name")
SCORE = FieldRef(table="metadata", name="score")


def test_query_samples__filter_and_sort(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for path, width in [("/a.png", 10), ("/b.png", 30), ("/c.png", 20)]:
        create_image(
            session=db_session, collection_id=collection_id, file_path_abs=path, width=width
        )
    request = SampleQueryRequest(
        query_expr=QueryExpr(
            match_expr=IntegerExpr(field=WIDTH, operator=OrdinalComparisonOperator.GT, value=15)
        ),
        sort=[SortKey(field=WIDTH, direction=SortDirection.desc)],
    )

    page = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=request
    )

    assert [sample.file_name for sample in page.samples] == ["b.png", "c.png"]
    assert page.samples[0].tags is None
    assert page.next_cursor is None


def test_query_samples__annotation_filter(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    create_image(session=db_session, collection_id=collection_id)
    subexpr = _width_filter(table="object_detection")
    request = SampleQueryRequest(
        query_expr=QueryExpr(match_expr=ObjectDetectionMatchExpr(subexpr=subexpr))
    )

    page = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=request
    )

    assert page.samples == []


@pytest.mark.parametrize("table", ["video", "object_detection"])
def test_query_samples__filter_field_of_other_table__raises(
    db_session: Session, table: str
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    request = SampleQueryRequest(query_expr=QueryExpr(match_expr=_width_filter(table=table)))

    with pytest.raises(QueryExprError, match="not valid here"):
        sample_query_service.query_samples(
            session=db_session, collection_id=collection_id, request=request
        )


@pytest.mark.parametrize("sort", [[], [SortKey(field=WIDTH)]])
def test_query_samples__pages(
    db_session: Session, sort: list[SortKey | EvaluationMetricSortKey]
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for path in ["/a.png", "/b.png", "/c.png", "/d.png", "/e.png"]:
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path, width=7)
    request = SampleQueryRequest(sort=sort, limit=2)

    sample_ids = []
    while True:
        page = sample_query_service.query_samples(
            session=db_session, collection_id=collection_id, request=request
        )
        sample_ids += [sample.sample_id for sample in page.samples]
        if page.next_cursor is None:
            break
        request = request.model_copy(update={"cursor": page.next_cursor})

    assert len(sample_ids) == 5
    assert len(set(sample_ids)) == 5


def test_query_samples__include_tags(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    tagged = create_image(session=db_session, collection_id=collection_id, file_path_abs="/a.png")
    create_image(session=db_session, collection_id=collection_id, file_path_abs="/b.png")
    for name in ["b", "a"]:
        tag = create_tag(session=db_session, collection_id=collection_id, tag_name=name)
        tag_resolver.add_sample_ids_to_tag_id(
            session=db_session, tag_id=tag.tag_id, sample_ids=[tagged.sample_id]
        )
    request = SampleQueryRequest(include=[SampleInclude.TAGS])

    page = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=request
    )

    assert {s.file_name: s.tags for s in page.samples} == {"a.png": ["a", "b"], "b.png": []}


def test_query_samples__cursor_of_other_sort__raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for path in ["/a.png", "/b.png"]:
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
    page = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=SampleQueryRequest(limit=1)
    )
    request = SampleQueryRequest(sort=[SortKey(field=WIDTH)], cursor=page.next_cursor)

    with pytest.raises(ValueError, match="different query"):
        sample_query_service.query_samples(
            session=db_session, collection_id=collection_id, request=request
        )


def test_query_samples__offset_only_on_first_page(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    for path in ["/a.png", "/b.png", "/c.png", "/d.png"]:
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
    request = SampleQueryRequest(sort=[SortKey(field=FILE_NAME)], limit=1, offset=1)

    first = sample_query_service.query_samples(
        session=db_session, collection_id=collection_id, request=request
    )
    second = sample_query_service.query_samples(
        session=db_session,
        collection_id=collection_id,
        request=request.model_copy(update={"cursor": first.next_cursor}),
    )

    assert [sample.file_name for sample in first.samples] == ["b.png"]
    assert [sample.file_name for sample in second.samples] == ["c.png"]


@pytest.mark.parametrize(
    "after",
    [
        [None, "00000000-0000-0000-0000-000000000001"],
        ["7", "00000000-0000-0000-0000-000000000001"],
        [7, 123],
    ],
)
def test_query_samples__cursor_values_not_valid__raises(
    db_session: Session, after: list[object]
) -> None:
    collection_id = create_collection(session=db_session).collection_id
    request = SampleQueryRequest(sort=[SortKey(field=WIDTH)])
    query_hash = sample_query_cursor.query_hash(collection_id=collection_id, request=request)
    cursor = sample_query_cursor.encode(query_hash=query_hash, after=after)

    with pytest.raises(ValueError, match="not valid"):
        sample_query_service.query_samples(
            session=db_session,
            collection_id=collection_id,
            request=request.model_copy(update={"cursor": cursor}),
        )


@pytest.mark.parametrize(
    ("request_", "error"),
    [
        (SampleQueryRequest(include=[SampleInclude.METADATA]), ValueError),
        (
            SampleQueryRequest(sort=[SortKey(field=FieldRef(table="video", name="fps"))]),
            QueryExprError,
        ),
    ],
)
def test_query_samples__not_supported__raises(
    db_session: Session, request_: SampleQueryRequest, error: type[Exception]
) -> None:
    collection_id = create_collection(session=db_session).collection_id

    with pytest.raises(error):
        sample_query_service.query_samples(
            session=db_session, collection_id=collection_id, request=request_
        )


@pytest.mark.parametrize("direction", [SortDirection.asc, SortDirection.desc])
def test_query_samples__metadata_sort__pages_in_order_of_sql_path(
    db_session: Session, direction: SortDirection
) -> None:
    collection = create_collection(session=db_session)
    images = [
        create_image(session=db_session, collection_id=collection.collection_id, file_path_abs=p)
        for p in ["/a.png", "/b.png", "/c.png", "/d.png", "/e.png"]
    ]
    metadata_resolver.bulk_update_metadata(
        session=db_session,
        sample_metadata=[
            (images[0].sample_id, {"score": 3}),
            (images[1].sample_id, {"score": 10}),
            (images[2].sample_id, {"score": 3}),
            (images[3].sample_id, {"other": 1}),
        ],
    )
    order_by = OrderByMetadataField(field_name="score")
    sql_query = DatasetQuery(dataset=collection, session=db_session).order_by(
        order_by.asc() if direction == SortDirection.asc else order_by.desc()
    )
    request = SampleQueryRequest(sort=[SortKey(field=SCORE, direction=direction)], limit=2)

    sample_ids = _all_sample_ids(
        session=db_session, collection_id=collection.collection_id, request=request
    )

    assert sample_ids == [sample.sample_id for sample in sql_query]


def test_query_samples__evaluation_metric_sort(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    low, high, missing = (
        create_image(session=db_session, collection_id=collection_id, file_path_abs=path)
        for path in ["/low.png", "/high.png", "/missing.png"]
    )
    run = create_run(session=db_session, collection_id=collection_id, name="run")
    create_sample_metrics(
        session=db_session,
        run_id=run.id,
        sample_metrics=[
            SampleMetricStub(sample_id=low.sample_id, metrics={"miou": 0.2}),
            SampleMetricStub(sample_id=high.sample_id, metrics={"miou": 0.8}),
        ],
    )
    sort_key = EvaluationMetricSortKey(
        run_name="run", metric_name="miou", direction=SortDirection.desc
    )
    request = SampleQueryRequest(sort=[sort_key], limit=1, offset=1)

    sample_ids = _all_sample_ids(session=db_session, collection_id=collection_id, request=request)

    assert sample_ids == [low.sample_id, missing.sample_id]


def test_query_samples__offset_paging_with_unknown_sort_field__raises(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    request = SampleQueryRequest(
        sort=[SortKey(field=SCORE), SortKey(field=FieldRef(table="video", name="fps"))]
    )

    with pytest.raises(QueryExprError, match=r"Unknown sort field: video\.fps"):
        sample_query_service.query_samples(
            session=db_session, collection_id=collection_id, request=request
        )


def _all_sample_ids(
    session: Session, collection_id: UUID, request: SampleQueryRequest
) -> list[UUID]:
    sample_ids = []
    while True:
        page = sample_query_service.query_samples(
            session=session, collection_id=collection_id, request=request
        )
        sample_ids += [sample.sample_id for sample in page.samples]
        if page.next_cursor is None:
            return sample_ids
        request = request.model_copy(update={"cursor": page.next_cursor, "offset": 0})


def _width_filter(table: str) -> IntegerExpr:
    width = FieldRef(table=table, name="width")
    return IntegerExpr(field=width, operator=OrdinalComparisonOperator.GT, value=1)
