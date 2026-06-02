"""Tests for the db_array module."""

from __future__ import annotations

import uuid

import pytest
from duckdb_engine import Dialect
from sqlalchemy.dialects import postgresql, sqlite
from sqlmodel import Session, col, select

from lightly_studio.db_array import in_array
from lightly_studio.models.sample import SampleTable
from tests.helpers_resolvers import create_collection, create_image


def test_in_array__postgresql() -> None:
    """PostgreSQL compiles to a single-parameter ``= ANY(:array)``, not an expanding IN."""
    expr = in_array(col(SampleTable.sample_id), [uuid.uuid4(), uuid.uuid4()])
    result = str(expr.compile(dialect=postgresql.dialect()))  # type: ignore[no-untyped-call]
    assert "= ANY" in result
    assert " IN " not in result


def test_in_array__duckdb() -> None:
    """DuckDB compiles to an ordinary expanding IN."""
    expr = in_array(col(SampleTable.sample_id), [uuid.uuid4(), uuid.uuid4()])
    result = str(expr.compile(dialect=Dialect()))
    assert " IN " in result
    assert "ANY" not in result


def test_in_array__unsupported() -> None:
    expr = in_array(col(SampleTable.sample_id), [uuid.uuid4()])
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        expr.compile(dialect=sqlite.dialect())


def test_in_array__returns_matching_rows(db_session: Session) -> None:
    collection_id = create_collection(session=db_session).collection_id
    images = [
        create_image(session=db_session, collection_id=collection_id, file_path_abs=f"/p/{i}.png")
        for i in range(3)
    ]
    wanted = [images[0].sample_id, images[2].sample_id]

    result = db_session.exec(
        select(SampleTable).where(in_array(col(SampleTable.sample_id), wanted))
    ).all()

    assert {sample.sample_id for sample in result} == set(wanted)


def test_in_array__exceeds_postgres_param_limit(db_session: Session) -> None:
    # More ids than PostgreSQL's 65,535-parameter cap.
    sample_ids = [uuid.uuid4() for _ in range(70_000)]
    result = db_session.exec(
        select(SampleTable).where(in_array(col(SampleTable.sample_id), sample_ids))
    ).all()
    assert result == []
