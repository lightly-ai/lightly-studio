"""Tests for db_types module."""

from __future__ import annotations

from sqlalchemy import ARRAY, Float, create_mock_engine

from lightly_studio.db_manager import DatabaseEngine
from lightly_studio.db_types import VectorType


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

    def test_load_dialect_impl__postgresql(self) -> None:
        """VectorType returns pgvector VECTOR for PostgreSQL dialect."""
        from pgvector.sqlalchemy import Vector

        # Use a mock engine since we don't have a test Postgres connection yet.
        engine = create_mock_engine("postgresql://", executor=lambda *_args, **_kwargs: None)
        dialect = engine.dialect
        vector_type = VectorType()
        result = vector_type.load_dialect_impl(dialect=dialect)
        assert isinstance(result, Vector)
