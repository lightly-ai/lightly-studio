"""Tests for db_types module."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from pgvector.sqlalchemy import Vector
from sqlalchemy import ARRAY, Float
from sqlalchemy.dialects import postgresql, sqlite
from sqlmodel import Session, select

from lightly_studio.database import db_vector
from lightly_studio.database.db_vector import VectorType


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


def test_inner_product__duckdb() -> None:
    """inner_product compiles to list_inner_product without casts for DuckDB."""
    expr = db_vector.inner_product(sqlalchemy.column("col1"), sqlalchemy.column("col2"))
    result = expr.compile(dialect=Dialect())
    assert str(result) == "list_inner_product(col1, col2)"


def test_inner_product__postgresql() -> None:
    """inner_product compiles to inner_product with ::vector casts for PostgreSQL."""
    expr = db_vector.inner_product(sqlalchemy.column("col1"), sqlalchemy.column("col2"))
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "inner_product(col1::vector, col2::vector)"


def test_inner_product__from_session(db_session: Session) -> None:
    vector = sqlalchemy.cast(sqlalchemy.literal([1.0, 2.0, 3.0], type_=ARRAY(Float)), VectorType())
    direction = sqlalchemy.bindparam("direction", value=[4.0, -5.0, 0.5], type_=ARRAY(Float))

    result = db_session.exec(select(db_vector.inner_product(vector, direction))).one()

    # 1 * 4 + 2 * (-5) + 3 * 0.5 = -4.5
    assert result == pytest.approx(-4.5)


def test_loaded_vector__postgresql() -> None:
    """loaded_vector compiles to subvector(col, 1, dimension) for PostgreSQL."""
    expr = db_vector.loaded_vector(sqlalchemy.column("col1"), sqlalchemy.literal_column("3"))
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "subvector(col1, 1, 3)"
