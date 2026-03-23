"""Tests for db_types module."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Float
from sqlalchemy.dialects import postgresql, sqlite
from sqlmodel import Session

from lightly_studio import db_vector
from lightly_studio.db_vector import VectorType


def test_load_dialect_impl__from_session(db_session: Session) -> None:
    """VectorType returns the correct column type for the active database dialect."""
    assert db_session.bind is not None
    dialect = db_session.bind.dialect
    vector_type = VectorType()
    result = vector_type.load_dialect_impl(dialect=dialect)
    if dialect.name == "postgresql":
        assert isinstance(result, Vector)
    else:
        assert isinstance(result, ARRAY)
        assert isinstance(result.item_type, Float)


def test_load_dialect_impl__unsupported() -> None:
    dialect = sqlite.dialect()
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
        expr.compile(dialect=sqlite.dialect())


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
        expr.compile(dialect=sqlite.dialect())
