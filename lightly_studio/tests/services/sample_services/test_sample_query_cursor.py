from __future__ import annotations

import base64
from datetime import datetime, timezone
from uuid import UUID

import pytest

from lightly_studio.models.query_expr import (
    FieldRef,
    IntegerExpr,
    OrdinalComparisonOperator,
    QueryExpr,
)
from lightly_studio.models.sample_query import SampleQueryRequest, SortKey
from lightly_studio.models.sort_direction import SortDirection
from lightly_studio.services.sample_services import sample_query_cursor

COLLECTION_ID = UUID("00000000-0000-0000-0000-000000000001")
SAMPLE_ID = UUID("00000000-0000-0000-0000-000000000002")
WIDTH = FieldRef(table="image", name="width")


def test_query_hash__same_filter_and_sort__same_hash() -> None:
    request = SampleQueryRequest(sort=[SortKey(field=WIDTH)])
    other = request.model_copy(update={"limit": 10, "cursor": "abc"})

    assert sample_query_cursor.query_hash(
        collection_id=COLLECTION_ID, request=request
    ) == sample_query_cursor.query_hash(collection_id=COLLECTION_ID, request=other)


@pytest.mark.parametrize(
    "other",
    [
        SampleQueryRequest(sort=[SortKey(field=WIDTH, direction=SortDirection.desc)]),
        SampleQueryRequest(
            query_expr=QueryExpr(
                match_expr=IntegerExpr(
                    field=WIDTH,
                    operator=OrdinalComparisonOperator.GT,
                    value=1,
                )
            )
        ),
    ],
)
def test_query_hash__other_filter_or_sort__other_hash(other: SampleQueryRequest) -> None:
    request = SampleQueryRequest()

    assert sample_query_cursor.query_hash(
        collection_id=COLLECTION_ID, request=request
    ) != sample_query_cursor.query_hash(collection_id=COLLECTION_ID, request=other)


def test_encode_decode() -> None:
    created_at = datetime(2026, 1, 2, 3, 4, 5, tzinfo=timezone.utc)

    cursor = sample_query_cursor.encode(query_hash="q1", after=[created_at, 7, SAMPLE_ID])

    assert "=" not in cursor
    assert sample_query_cursor.decode(cursor=cursor, query_hash="q1") == [
        "2026-01-02T03:04:05+00:00",
        7,
        str(SAMPLE_ID),
    ]


def test_decode__other_query__raises() -> None:
    cursor = sample_query_cursor.encode(query_hash="q1", after=[SAMPLE_ID])

    with pytest.raises(ValueError, match="different query"):
        sample_query_cursor.decode(cursor=cursor, query_hash="q2")


@pytest.mark.parametrize("cursor", ["not a cursor", "e30", "eyJ2IjoyfQ"])
def test_decode__not_valid__raises(cursor: str) -> None:
    with pytest.raises(ValueError, match="not valid"):
        sample_query_cursor.decode(cursor=cursor, query_hash="q1")


def test_decode__deeply_nested__raises() -> None:
    nested = "[" * 100_000 + "]" * 100_000
    cursor = base64.urlsafe_b64encode(nested.encode()).decode()

    with pytest.raises(ValueError, match="not valid"):
        sample_query_cursor.decode(cursor=cursor, query_hash="q1")


def test_decode__invalid_characters__raises() -> None:
    cursor = sample_query_cursor.encode(query_hash="q1", after=[SAMPLE_ID])

    with pytest.raises(ValueError, match="not valid"):
        sample_query_cursor.decode(cursor=cursor + "!!!!", query_hash="q1")
