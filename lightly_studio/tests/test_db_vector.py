"""Tests for db_types module."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Float
from sqlalchemy.dialects import postgresql, sqlite

from lightly_studio import db_vector
from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.db_vector import VectorType
from sqlmodel import Session


@pytest.mark.duckdb_only
def test_load_dialect_impl__duckdb(db_session: Session) -> None:
    """VectorType returns ARRAY(Float) for DuckDB dialect."""
    dialect = db_session.bind.dialect
    vector_type = VectorType()
    result = vector_type.load_dialect_impl(dialect=dialect)
    assert isinstance(result, ARRAY)
    assert isinstance(result.item_type, Float)

@pytest.mark.postgres_only
def test_load_dialect_impl__postgresql(
        db_session: Session,
) -> None:
    """VectorType returns pgvector VECTOR for a real PostgreSQL dialect."""
    dialect = db_session.bind.dialect
    vector_type = db_vector.VectorType()
    result = vector_type.load_dialect_impl(dialect=dialect)
    assert isinstance(result, Vector)

def test_load_dialect_impl__unsupported() -> None:
    # SQLAlchemy dialect factory functions lack type stubs.
    dialect = sqlite.dialect()  # type: ignore[no-untyped-call]
    vector_type = db_vector.VectorType()
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        vector_type.load_dialect_impl(dialect=dialect)


def test_cosine_distance__duckdb() -> None:
    """cosine_distance compiles to <=> without casts for DuckDB."""
    expr = db_vector.cosine_distance(sqlalchemy.column("col1"), sqlalchemy.column("col2"))
    result = expr.compile(dialect=Dialect())
    assert str(result) == "(col1 <=> col2)"

def test_cosine_distance__postgresql() -> None:
    """cosine_distance compiles to <=> with ::vector casts for PostgreSQL."""
    expr = db_vector.cosine_distance(sqlalchemy.column("col1"), sqlalchemy.column("col2"))
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(col1::vector <=> col2::vector)"

def test_cosine_distance__unsupported() -> None:
    expr = db_vector.cosine_distance(sqlalchemy.column("col1"), sqlalchemy.column("col2"))
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        # SQLAlchemy dialect factory functions lack type stubs.
        expr.compile(dialect=sqlite.dialect())  # type: ignore[no-untyped-call]


def test_vector_element__duckdb() -> None:
    """vector_element compiles to col[index] for DuckDB."""
    expr = db_vector.vector_element(sqlalchemy.column("col1"), sqlalchemy.literal_column("1"))
    result = expr.compile(dialect=Dialect())
    assert str(result) == "col1[1]"

def test_vector_element__postgresql() -> None:
    """vector_element compiles to (col::real[])[index] for PostgreSQL."""
    expr = db_vector.vector_element(sqlalchemy.column("col1"), sqlalchemy.literal_column("1"))
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(col1::real[])[1]"

def test_vector_element__unsupported() -> None:
    expr = db_vector.vector_element(sqlalchemy.column("col1"), sqlalchemy.literal_column("1"))
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        # SQLAlchemy dialect factory functions lack type stubs.
        expr.compile(dialect=sqlite.dialect())  # type: ignore[no-untyped-call]
