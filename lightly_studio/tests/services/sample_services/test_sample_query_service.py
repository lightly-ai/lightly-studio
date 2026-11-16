from __future__ import annotations

import pytest
from sqlmodel import Session

from lightly_studio.errors import QueryExprError
from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    ObjectDetectionMatchExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import SampleInclude, SampleQueryRequest, SortKey
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.services.sample_services import sample_query_service
from tests.helpers_resolvers import create_collection, create_image

WIDTH = FieldRef(table="image", name="width")


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


def _width_filter(table: str) -> IntegerExpr:
    width = FieldRef(table=table, name="width")
    return IntegerExpr(field=width, operator=OrdinalComparisonOperator.GT, value=1)
