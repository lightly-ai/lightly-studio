"""Tests for db_types module."""

from __future__ import annotations

import sys

import pytest
from sqlalchemy import ARRAY, Float, column, create_mock_engine
from sqlalchemy.dialects import sqlite

from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.db_vector_type import VectorType, cosine_distance


class TestVectorType:
    def test_load_dialect_impl__duckdb(self) -> None:
        """VectorType returns ARRAY(Float) for DuckDB dialect."""
        db = DatabaseEngine(engine_url="duckdb:///:memory:", single_threaded=True)
        dialect = db._engine.dialect
        vector_type = VectorType()
        result = vector_type.load_dialect_impl(dialect=dialect)
        assert isinstance(result, ARRAY)
        assert isinstance(result.item_type, Float)
        db.close()

    # TODO(Mihnea, 02/2026): Remove the skip once we deprecate support for Python 3.8.
    @pytest.mark.skipif(
        sys.version_info < (3, 9),
        reason="pgvector is only installed for Python >= 3.9",
    )
    def test_load_dialect_impl__postgresql(self) -> None:
        """VectorType returns pgvector VECTOR for PostgreSQL dialect."""
        from pgvector.sqlalchemy import Vector

        # Use a mock engine since we don't have a test Postgres connection yet.
        engine = create_mock_engine("postgresql://", executor=lambda *_args, **_kwargs: None)
        dialect = engine.dialect
        vector_type = VectorType()
        result = vector_type.load_dialect_impl(dialect=dialect)
        assert isinstance(result, Vector)

    def test_load_dialect_impl__unsupported(self) -> None:
        dialect = sqlite.dialect()
        vector_type = VectorType()
        with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
            vector_type.load_dialect_impl(dialect=dialect)


class TestCosineDistanceCompilation:
    def test_compile__duckdb(self) -> None:
        """cosine_distance compiles to <=> without casts for DuckDB."""
        from duckdb_engine import Dialect as DuckDBDialect

        expr = cosine_distance(column("col1"), column("col2"))
        result = expr.compile(dialect=DuckDBDialect())
        assert str(result) == "(col1 <=> col2)"

    # TODO(Mihnea, 02/2026): Remove the skip once we deprecate support for Python 3.8.
    @pytest.mark.skipif(
        sys.version_info < (3, 9),
        reason="pgvector is only installed for Python >= 3.9",
    )
    def test_compile__postgresql(self) -> None:
        """cosine_distance compiles to <=> with ::vector casts for PostgreSQL."""
        from sqlalchemy.dialects import postgresql

        expr = cosine_distance(column("col1"), column("col2"))
        result = expr.compile(dialect=postgresql.dialect())
        assert str(result) == "(col1::vector <=> col2::vector)"

    def test_compile__unsupported(self) -> None:
        expr = cosine_distance(column("col1"), column("col2"))
        with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
            expr.compile(dialect=sqlite.dialect())
