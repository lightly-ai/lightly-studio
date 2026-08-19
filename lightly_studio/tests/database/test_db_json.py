"""Tests for dialect-aware JSON extraction functions."""

from __future__ import annotations

from typing import Any

import pytest
import sqlalchemy
from duckdb_engine import Dialect
from sqlalchemy.dialects import postgresql

from lightly_studio.database import db_json

# Both databases speak the same JSON operators, so every expression below has to
# compile identically for each of them.
_DIALECTS = [Dialect(), postgresql.dialect()]  # type: ignore[no-untyped-call]

_COLUMN = sqlalchemy.column("data", sqlalchemy.JSON)

# A key that closes the string literal and appends SQL, if it were interpolated.
_INJECTION_KEY = "x') AS FLOAT), (SELECT 1 FROM secrets"
_SPECIAL_KEYS = [
    _INJECTION_KEY,
    "owner's key",
    'say "hi"',
    "back\\slash",
    "path/to~key",
    # Closes the string literal and starts a new statement.
    "x'); DROP TABLE victim; --",
    # Concatenates a subquery into the value.
    "'||(SELECT count(*) FROM victim)||'",
]

# Keys that DuckDB reads as JSONPath or as a JSON Pointer unless they are bound as
# pointers: "$" addresses the whole document, "$.temp" addresses another key, "$x"
# raises, and a leading "/" starts a pointer. PostgreSQL reads all of them as keys.
_PATH_SYNTAX_KEYS = ["$", "$.temp", "$x", "$[0]", "/a", "/", "~1"]


def _compile(expression: Any, dialect: Any) -> Any:
    return expression.compile(dialect=dialect)


def _every_entry_point(field: str) -> list[Any]:
    """Return one expression per entry point, all reading the same field."""
    return [
        db_json._json_extract(column=_COLUMN, field=field),
        db_json.json_extract_as_text(column=_COLUMN, field=field),
        db_json.json_extract_as_float(column=_COLUMN, field=field),
        db_json.json_extract_key_as_text(column=_COLUMN, key=field),
    ]


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("temperature", ["temperature"]),
        ("test_dict.int_key", ["test_dict", "int_key"]),
        ("a.b.c", ["a", "b", "c"]),
        ("test_dict.nested_list[0]", ["test_dict", "nested_list", 0]),
        ("nested_list[10][2]", ["nested_list", 10, 2]),
        ("nested_list[-1]", ["nested_list", -1]),
        # Only integer brackets are indices; anything else becomes a key of its own.
        ("weird[key]", ["weird", "[key]"]),
        ("weird[0x1]", ["weird", "[0x1]"]),
        # The largest indices PostgreSQL subscripts accept.
        ("nested_list[2147483647]", ["nested_list", 2147483647]),
        ("nested_list[-2147483648]", ["nested_list", -2147483648]),
    ],
)
def test_parse_field_path(field: str, expected: list[str | int]) -> None:
    assert db_json._parse_field_path(field) == expected


@pytest.mark.parametrize("index", ["2147483648", "-2147483649", "99999999999999999999"])
def test_parse_field_path__out_of_range_index_stays_a_key(index: str) -> None:
    """An index PostgreSQL cannot subscript with addresses nothing, so it stays a key."""
    assert db_json._parse_field_path(f"nested_list[{index}]") == ["nested_list", f"[{index}]"]


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract__simple_key(dialect: Any) -> None:
    result = _compile(db_json._json_extract(column=_COLUMN, field="temperature"), dialect)
    assert str(result) == "data -> %(param_1)s"
    assert result.params == {"param_1": "temperature"}


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract__nested_key(dialect: Any) -> None:
    """Each segment is its own bound step, so no key can be read as path syntax."""
    result = _compile(db_json._json_extract(column=_COLUMN, field="test_dict.int_key"), dialect)
    assert str(result) == "(data -> %(param_1)s) -> %(param_2)s"
    assert result.params == {"param_1": "test_dict", "param_2": "int_key"}


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract__array_index(dialect: Any) -> None:
    result = _compile(db_json._json_extract(column=_COLUMN, field="nested_list[0]"), dialect)
    assert str(result) == "(data -> %(param_1)s) -> %(param_2)s"
    assert result.params == {"param_1": "nested_list", "param_2": 0}


@pytest.mark.parametrize("dialect", _DIALECTS)
@pytest.mark.parametrize("index", [-1, -3])
def test_json_extract__negative_index(dialect: Any, index: int) -> None:
    """Both databases subscript from the end natively, so the index passes straight through."""
    result = _compile(db_json._json_extract(column=_COLUMN, field=f"nested_list[{index}]"), dialect)
    assert result.params == {"param_1": "nested_list", "param_2": index}


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract__out_of_range_index_is_a_bound_key(dialect: Any) -> None:
    """An index wider than int32 raises when subscripted, so it is bound as a key instead."""
    result = _compile(
        db_json._json_extract(column=_COLUMN, field="nested_list[2147483648]"), dialect
    )
    assert result.params == {"param_1": "nested_list", "param_2": "[2147483648]"}


@pytest.mark.parametrize("dialect", _DIALECTS)
@pytest.mark.parametrize("field", _SPECIAL_KEYS)
def test_json_extract__special_key_is_bound(dialect: Any, field: str) -> None:
    """Special characters stay inside the parameter and never reach the statement."""
    result = _compile(db_json._json_extract(column=_COLUMN, field=field), dialect)
    assert str(result) == "data -> %(param_1)s"
    assert result.params == {"param_1": field}


@pytest.mark.parametrize("dialect", _DIALECTS)
@pytest.mark.parametrize("field", [f"weird[{_INJECTION_KEY}]", "weird[0; DROP TABLE t]"])
def test_json_extract__non_integer_index_is_bound(dialect: Any, field: str) -> None:
    """Brackets holding anything but an integer are bound as keys, so they smuggle nothing."""
    result = _compile(db_json._json_extract(column=_COLUMN, field=field), dialect)
    assert str(result) == "(data -> %(param_1)s) -> %(param_2)s"


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract_as_float(dialect: Any) -> None:
    result = _compile(db_json.json_extract_as_float(column=_COLUMN, field="temperature"), dialect)
    assert str(result) == "CAST(data ->> %(param_1)s AS FLOAT)"
    assert result.params == {"param_1": "temperature"}


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract_as_text(dialect: Any) -> None:
    result = _compile(db_json.json_extract_as_text(column=_COLUMN, field="temperature"), dialect)
    assert str(result) == "CAST(data ->> %(param_1)s AS VARCHAR)"
    assert result.params == {"param_1": "temperature"}


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract_as_text__presence_test_uses_the_text_operator(dialect: Any) -> None:
    """``->>`` is SQL NULL for a stored JSON null, while ``->`` yields the JSON null.

    So a presence test has to read the value as text; the raw index would count a row
    whose key is present but null.
    """
    expression = db_json.json_extract_as_text(column=_COLUMN, field="temperature").isnot(None)

    result = _compile(expression, dialect)

    assert str(result) == "CAST((data ->> %(param_1)s) AS VARCHAR) IS NOT NULL"


@pytest.mark.parametrize("dialect", _DIALECTS)
@pytest.mark.parametrize("key", ["site.name", *_SPECIAL_KEYS])
def test_json_extract_key_as_text__key_is_literal_and_bound(dialect: Any, key: str) -> None:
    """The whole argument is one key, so a dot in it does not step into a nested object."""
    result = _compile(db_json.json_extract_key_as_text(column=_COLUMN, key=key), dialect)
    assert str(result) == "CAST(data ->> %(param_1)s AS VARCHAR)"
    assert result.params == {"param_1": key}


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("$", "/$"),
        ("$.temp", "/$.temp"),
        ("$x", "/$x"),
        ("/a", "/~1a"),
        ("/", "/~1"),
        ("~1", "/~01"),
        ("path/to~key", "/path~1to~0key"),
        ("temp", "/temp"),
    ],
)
def test_json_key_type__duckdb_gets_a_pointer(key: str, expected: str) -> None:
    """DuckDB reads a leading "$" as JSONPath and a leading "/" as a pointer.

    Binding every key as a one-segment pointer removes the ambiguity.
    """
    key_type = db_json._JsonKeyType()
    assert key_type.process_bind_param(value=key, dialect=Dialect()) == expected


@pytest.mark.parametrize("key", _PATH_SYNTAX_KEYS)
def test_json_key_type__postgres_gets_the_raw_key(key: str) -> None:
    """PostgreSQL reads a key and nothing else, so it needs no pointer."""
    key_type = db_json._JsonKeyType()
    postgres = postgresql.dialect()  # type: ignore[no-untyped-call]
    assert key_type.process_bind_param(value=key, dialect=postgres) == key


@pytest.mark.parametrize("dialect", _DIALECTS)
@pytest.mark.parametrize("field", _SPECIAL_KEYS)
def test_json_extract__special_key_never_reaches_the_statement(dialect: Any, field: str) -> None:
    """Every entry point binds the key, so no payload becomes part of the SQL text."""
    for expression in _every_entry_point(field):
        sql = str(_compile(expression, dialect))

        assert field not in sql
        # Nothing the payloads carry survives into the statement.
        assert ";" not in sql
        assert "drop" not in sql.lower()
        assert "select" not in sql.lower()


@pytest.mark.parametrize("dialect", _DIALECTS)
def test_json_extract__repeated_renders_share_one_parameter(dialect: Any) -> None:
    """One parameter per key, so GROUP BY renders the same expression as SELECT."""
    expr = db_json._json_extract(column=_COLUMN, field="score")
    query = sqlalchemy.select(expr).group_by(expr)

    result = _compile(query, dialect)

    assert len(result.params) == 1
    select_sql, group_by_sql = str(result).split(" GROUP BY ")
    assert group_by_sql.strip() in select_sql
