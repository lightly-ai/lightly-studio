"""Tests for dialect-aware JSON extraction functions."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from sqlalchemy.dialects import postgresql, sqlite

from lightly_studio import db_json


def test_build_pg_json_accessor__simple_key() -> None:
    result = db_json._build_pg_json_accessor(column="metadata.data", field="temperature")
    assert result == "metadata.data->>'temperature'"


def test_build_pg_json_accessor__nested_key() -> None:
    result = db_json._build_pg_json_accessor(column="metadata.data", field="test_dict.int_key")
    assert result == "metadata.data->'test_dict'->>'int_key'"


def test_build_pg_json_accessor__deeply_nested_key() -> None:
    result = db_json._build_pg_json_accessor(column="metadata.data", field="a.b.c")
    assert result == "metadata.data->'a'->'b'->>'c'"


def test_build_pg_json_accessor__array_index() -> None:
    result = db_json._build_pg_json_accessor(
        column="metadata.data", field="test_dict.nested_list[0]"
    )
    assert result == "metadata.data->'test_dict'->'nested_list'->>0"


def test_build_pg_json_accessor__cast_to_float() -> None:
    result = db_json._build_pg_json_accessor(
        column="metadata.data", field="temperature", cast_to_float=True
    )
    assert result == "(metadata.data->>'temperature')::float"


def test_build_pg_json_accessor__nested_cast_to_float() -> None:
    result = db_json._build_pg_json_accessor(
        column="metadata.data", field="test_dict.int_key", cast_to_float=True
    )
    assert result == "(metadata.data->'test_dict'->>'int_key')::float"


def test_build_pg_json_accessor__custom_column() -> None:
    result = db_json._build_pg_json_accessor(column="my_table.json_col", field="key")
    assert result == "my_table.json_col->>'key'"


def test_json_extract__duckdb_simple_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="temperature")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, '$.temperature')"


def test_json_extract__duckdb_nested_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.int_key")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, '$.test_dict.int_key')"


def test_json_extract__duckdb_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="temperature", cast_to_float=True
    )
    result = expr.compile(dialect=Dialect())
    assert str(result) == "CAST(json_extract(data, '$.temperature') AS FLOAT)"


def test_json_extract__duckdb_array_index() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.nested_list[0]")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, '$.test_dict.nested_list[0]')"


def test_json_extract__pg_simple_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="temperature")
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->>'temperature'"


def test_json_extract__pg_nested_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.int_key")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->'test_dict'->>'int_key'"


def test_json_extract__pg_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="temperature", cast_to_float=True
    )
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(data->>'temperature')::float"


def test_json_extract__pg_nested_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="test_dict.int_key", cast_to_float=True
    )
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(data->'test_dict'->>'int_key')::float"


def test_json_extract__pg_array_index() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.nested_list[0]")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->'test_dict'->'nested_list'->>0"


def test_json_extract__sqlite_raises() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="key")
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        # SQLAlchemy dialect factory functions lack type stubs.
        expr.compile(dialect=sqlite.dialect())  # type: ignore[no-untyped-call]


def test_json_literal__duckdb_string_value() -> None:
    """String values are JSON-encoded for DuckDB."""
    lit = db_json.json_literal("hello")
    type_ = lit.type
    assert isinstance(type_, db_json._JsonStringType)
    assert type_.process_bind_param(value="hello", dialect=Dialect()) == '"hello"'


def test_json_literal__pg_string_value() -> None:
    """String values pass through unchanged for PostgreSQL."""
    lit = db_json.json_literal("hello")
    type_ = lit.type
    assert isinstance(type_, db_json._JsonStringType)
    # SQLAlchemy dialect factory functions lack type stubs.
    assert type_.process_bind_param(value="hello", dialect=postgresql.dialect()) == "hello"  # type: ignore[no-untyped-call]


def test_json_literal__none() -> None:
    type_ = db_json._JsonStringType()
    assert type_.process_bind_param(value=None, dialect=Dialect()) is None


def test_json_literal__numeric_value() -> None:
    lit = db_json.json_literal(10)
    assert not isinstance(lit.type, db_json._JsonStringType)


def test_json_literal__float_value() -> None:
    lit = db_json.json_literal(1.23)
    assert not isinstance(lit.type, db_json._JsonStringType)
