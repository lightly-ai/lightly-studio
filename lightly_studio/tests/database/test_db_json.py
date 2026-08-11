"""Tests for dialect-aware JSON extraction functions."""

from __future__ import annotations

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from sqlalchemy.dialects import postgresql, sqlite

from lightly_studio.database import db_json


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("temperature", ["temperature"]),
        ("test_dict.int_key", ["test_dict", "int_key"]),
        ("a.b.c", ["a", "b", "c"]),
        ("test_dict.nested_list[0]", ["test_dict", "nested_list", 0]),
        ("nested_list[10][2]", ["nested_list", 10, 2]),
        # Only non-negative integer brackets are indices; anything else stays part of
        # the key, including "[-1]", which JSON Pointer cannot express.
        ("weird[key]", ["weird", "[key]"]),
        ("weird[0x1]", ["weird", "[0x1]"]),
        ("nested_list[-1]", ["nested_list", "[-1]"]),
    ],
)
def test_parse_field_path(field: str, expected: list[str | int]) -> None:
    assert db_json._parse_field_path(field) == expected


@pytest.mark.parametrize(
    ("segments", "expected"),
    [
        (["temperature"], "/temperature"),
        (["a", "b"], "/a/b"),
        (["a", "list", 0], "/a/list/0"),
        (["path/to~key"], "/path~1to~0key"),
        (["owner's key"], "/owner's key"),
    ],
)
def test_to_json_pointer(segments: list[str | int], expected: str) -> None:
    assert db_json._to_json_pointer(segments) == expected


def test_json_extract__duckdb_simple_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="temperature")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, %(param_1)s)"
    assert result.params == {"param_1": "/temperature"}


def test_json_extract__duckdb_nested_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.int_key")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, %(param_1)s)"
    assert result.params == {"param_1": "/test_dict/int_key"}


def test_json_extract__duckdb_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="temperature", cast_to_float=True
    )
    result = expr.compile(dialect=Dialect())
    assert str(result) == "CAST(json_extract(data, %(param_1)s) AS FLOAT)"
    assert result.params == {"param_1": "/temperature"}


def test_json_extract__duckdb_array_index() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.nested_list[0]")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract(data, %(param_1)s)"
    assert result.params == {"param_1": "/test_dict/nested_list/0"}


def test_json_extract__pg_simple_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="temperature")
    # SQLAlchemy dialect factory functions lack type stubs.
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->>%(param_1)s"
    assert result.params == {"param_1": "temperature"}


def test_json_extract__pg_nested_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.int_key")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->%(param_1)s->>%(param_2)s"
    assert result.params == {"param_1": "test_dict", "param_2": "int_key"}


def test_json_extract__pg_deeply_nested_key() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="a.b.c")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->%(param_1)s->%(param_2)s->>%(param_3)s"
    assert result.params == {"param_1": "a", "param_2": "b", "param_3": "c"}


def test_json_extract__pg_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="temperature", cast_to_float=True
    )
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(data->>%(param_1)s)::float"
    assert result.params == {"param_1": "temperature"}


def test_json_extract__pg_nested_cast_to_float() -> None:
    expr = db_json.json_extract(
        column=sqlalchemy.column("data"), field="test_dict.int_key", cast_to_float=True
    )
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(data->%(param_1)s->>%(param_2)s)::float"
    assert result.params == {"param_1": "test_dict", "param_2": "int_key"}


def test_json_extract__pg_array_index() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="test_dict.nested_list[0]")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->%(param_1)s->%(param_2)s->>0"
    assert result.params == {"param_1": "test_dict", "param_2": "nested_list"}


@pytest.mark.parametrize("dialect", [Dialect(), postgresql.dialect()])  # type: ignore[no-untyped-call]
def test_json_extract__repeated_renders_share_one_parameter(dialect: object) -> None:
    """One parameter per key, so GROUP BY renders the same expression as SELECT."""
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="score")
    query = sqlalchemy.select(expr).group_by(expr)

    result = query.compile(dialect=dialect)  # type: ignore[arg-type]

    assert len(result.params) == 1
    select_sql, group_by_sql = str(result).split(" GROUP BY ")
    assert group_by_sql.strip() in select_sql


# A key that closes the string literal and appends SQL, if it were interpolated.
_INJECTION_KEY = "x') AS FLOAT), (SELECT 1 FROM secrets"


@pytest.mark.parametrize("field", [_INJECTION_KEY, "owner's key", 'say "hi"', "back\\slash"])
def test_json_extract__duckdb_special_key_is_bound(field: str) -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field=field, cast_to_float=True)
    result = expr.compile(dialect=Dialect())
    assert str(result) == "CAST(json_extract(data, %(param_1)s) AS FLOAT)"
    assert result.params == {"param_1": f"/{field}"}


@pytest.mark.parametrize("field", [_INJECTION_KEY, "owner's key", 'say "hi"', "back\\slash"])
def test_json_extract__pg_special_key_is_bound(field: str) -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field=field, cast_to_float=True)
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "(data->>%(param_1)s)::float"
    assert result.params == {"param_1": field}


@pytest.mark.parametrize("field", [f"weird[{_INJECTION_KEY}]", "weird[0; DROP TABLE t]"])
def test_json_extract__pg_non_integer_index_is_bound(field: str) -> None:
    """Only integer indices render unquoted, so brackets cannot smuggle in SQL."""
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field=field)
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->%(param_1)s->>%(param_2)s"


def test_json_extract__sqlite_raises() -> None:
    expr = db_json.json_extract(column=sqlalchemy.column("data"), field="key")
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        expr.compile(dialect=sqlite.dialect())


def test_json_extract_string__duckdb() -> None:
    expr = db_json.json_extract_string(column=sqlalchemy.column("data"), field="location")
    result = expr.compile(dialect=Dialect())
    assert str(result) == "json_extract_string(data, %(param_1)s)"
    assert result.params == {"param_1": "location"}


def test_json_extract_string__postgresql() -> None:
    expr = db_json.json_extract_string(column=sqlalchemy.column("data"), field="location")
    result = expr.compile(dialect=postgresql.dialect())  # type: ignore[no-untyped-call]
    assert str(result) == "data->>%(param_1)s"
    assert result.params == {"param_1": "location"}


@pytest.mark.parametrize("field", ["site.name", "owner's site"])
def test_json_extract_string__special_key_is_bound(field: str) -> None:
    expr = db_json.json_extract_string(column=sqlalchemy.column("data"), field=field)
    duckdb_result = expr.compile(dialect=Dialect())
    postgres_result = expr.compile(
        dialect=postgresql.dialect()  # type: ignore[no-untyped-call]
    )

    assert str(duckdb_result) == "json_extract_string(data, %(param_1)s)"
    assert duckdb_result.params == {"param_1": field}
    assert str(postgres_result) == "data->>%(param_1)s"
    assert postgres_result.params == {"param_1": field}


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("site.name", "/site.name"),
        ("owner's site", "/owner's site"),
        ("path/to~site", "/path~1to~0site"),
    ],
)
def test_json_top_level_key_type__duckdb_path(field: str, expected: str) -> None:
    type_ = db_json._JsonTopLevelKeyType()
    assert type_.process_bind_param(value=field, dialect=Dialect()) == expected


def test_json_extract_string__sqlite_raises() -> None:
    expr = db_json.json_extract_string(column=sqlalchemy.column("data"), field="location")
    with pytest.raises(NotImplementedError, match="Unsupported dialect: sqlite"):
        expr.compile(dialect=sqlite.dialect())


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
