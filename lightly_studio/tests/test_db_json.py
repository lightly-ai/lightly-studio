"""Tests for dialect-aware JSON extraction functions."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from sqlalchemy.dialects import postgresql, sqlite

from lightly_studio import db_json
from lightly_studio.db_json import _build_pg_json_accessor


class TestBuildPgJsonAccessor:
    def test_build_pg_json_accessor__simple_key(self) -> None:
        result = _build_pg_json_accessor(column="metadata.data", field="temperature")
        assert result == "metadata.data->>'temperature'"

    def test_build_pg_json_accessor__nested_key(self) -> None:
        result = _build_pg_json_accessor(column="metadata.data", field="test_dict.int_key")
        assert result == "metadata.data->'test_dict'->>'int_key'"

    def test_build_pg_json_accessor__deeply_nested_key(self) -> None:
        result = _build_pg_json_accessor(column="metadata.data", field="a.b.c")
        assert result == "metadata.data->'a'->'b'->>'c'"

    def test_build_pg_json_accessor__array_index(self) -> None:
        result = _build_pg_json_accessor(column="metadata.data", field="test_dict.nested_list[0]")
        assert result == "metadata.data->'test_dict'->'nested_list'->>0"

    def test_build_pg_json_accessor__cast_to_float(self) -> None:
        result = _build_pg_json_accessor(
            column="metadata.data", field="temperature", cast_to_float=True
        )
        assert result == "(metadata.data->>'temperature')::float"

    def test_build_pg_json_accessor__nested_cast_to_float(self) -> None:
        result = _build_pg_json_accessor(
            column="metadata.data", field="test_dict.int_key", cast_to_float=True
        )
        assert result == "(metadata.data->'test_dict'->>'int_key')::float"

    def test_build_pg_json_accessor__custom_column(self) -> None:
        result = _build_pg_json_accessor(column="my_table.json_col", field="key")
        assert result == "my_table.json_col->>'key'"


class TestJsonExtractDuckDB:
    def test_json_extract__simple_key(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "temperature")
        result = expr.compile(dialect=Dialect())
        assert str(result) == "json_extract(data, '$.temperature')"

    def test_json_extract__nested_key(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "test_dict.int_key")
        result = expr.compile(dialect=Dialect())
        assert str(result) == "json_extract(data, '$.test_dict.int_key')"

    def test_json_extract__cast_to_float(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "temperature", cast_to_float=True)
        result = expr.compile(dialect=Dialect())
        assert str(result) == "CAST(json_extract(data, '$.temperature') AS FLOAT)"

    def test_json_extract__array_index(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "test_dict.nested_list[0]")
        result = expr.compile(dialect=Dialect())
        assert str(result) == "json_extract(data, '$.test_dict.nested_list[0]')"


class TestJsonExtractPostgreSQL:
    def test_json_extract__simple_key(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "temperature")
        # SQLAlchemy dialect factory functions lack type stubs.
        result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        assert str(result) == "data->>'temperature'"

    def test_json_extract__nested_key(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "test_dict.int_key")
        result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        assert str(result) == "data->'test_dict'->>'int_key'"

    def test_json_extract__cast_to_float(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "temperature", cast_to_float=True)
        result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        assert str(result) == "(data->>'temperature')::float"

    def test_json_extract__nested_cast_to_float(self) -> None:
        expr = db_json.json_extract(
            sqlalchemy.column("data"), "test_dict.int_key", cast_to_float=True
        )
        result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        assert str(result) == "(data->'test_dict'->>'int_key')::float"

    def test_json_extract__array_index(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "test_dict.nested_list[0]")
        result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
        assert str(result) == "data->'test_dict'->'nested_list'->>0"


class TestJsonExtractUnsupported:
    def test_json_extract__sqlite_raises(self) -> None:
        expr = db_json.json_extract(sqlalchemy.column("data"), "key")
        with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
            # SQLAlchemy dialect factory functions lack type stubs.
            expr.compile(dialect=sqlite.dialect())  # type: ignore[no-untyped-call]


class TestJsonLiteral:
    def test_json_literal__string_value_duckdb(self) -> None:
        """String values are JSON-encoded for DuckDB."""
        lit = db_json.json_literal("hello")
        type_ = lit.type
        assert isinstance(type_, db_json._JsonStringType)
        assert type_.process_bind_param("hello", Dialect()) == '"hello"'

    def test_json_literal__string_value_postgresql(self) -> None:
        """String values pass through unchanged for PostgreSQL."""
        lit = db_json.json_literal("hello")
        type_ = lit.type
        assert isinstance(type_, db_json._JsonStringType)
        # SQLAlchemy dialect factory functions lack type stubs.
        assert type_.process_bind_param("hello", postgresql.dialect()) == "hello"  # type: ignore[no-untyped-call]

    def test_json_literal__none(self) -> None:
        type_ = db_json._JsonStringType()
        assert type_.process_bind_param(None, Dialect()) is None

    def test_json_literal__numeric_value(self) -> None:
        lit = db_json.json_literal(10)
        assert not isinstance(lit.type, db_json._JsonStringType)

    def test_json_literal__float_value(self) -> None:
        lit = db_json.json_literal(1.23)
        assert not isinstance(lit.type, db_json._JsonStringType)
