"""Dialect-aware JSON extraction functions.

Thin wrappers over SQLAlchemy's JSON indexing, which compiles to the right operator
chain for DuckDB and PostgreSQL and binds every key as a parameter.

Two things decide which function to call. A *field* is a path (``a.b``, ``a.list[0]``)
while a *key* is one literal name, so ``json_extract_key_as_text`` reads ``a.b`` as a
key that contains a dot. And the raw expression from :func:`json_extract` yields
``json``, which neither database compares against a plain value and which PostgreSQL
cannot order or cast, so use it only to test for presence and reach for the
``_as_text`` and ``_as_float`` variants everywhere else.
"""

from __future__ import annotations

import functools
import operator
import re
from typing import Any, cast

import sqlalchemy
from sqlalchemy import ColumnElement, Text
from sqlalchemy.engine.interfaces import Dialect
from sqlalchemy.types import TypeDecorator

# Not DatabaseBackend.DUCKDB from db_manager: importing it here closes an import cycle
# through api.db_tables and the resolvers.
_DUCKDB_DIALECT = "duckdb"

_ARRAY_INDEX_PATTERN = re.compile(r"^\[(-?[0-9]+)\]$")

# PostgreSQL's "->" subscript takes a 32-bit integer; a wider one raises rather than
# missing. Out-of-range indices address nothing anyway.
_INT32_MIN = -(2**31)
_INT32_MAX = 2**31 - 1


def json_extract(column: Any, field: str) -> ColumnElement[Any]:
    """Index into a JSON column by field path.

    Compiles to a ``col -> :key`` chain, so keys are bound rather than interpolated
    into SQL and quotes or dots in them cannot alter the statement.

    ``field`` supports dot-separated paths (``a.b.c``) and array indices
    (``a.list[0]``), including negative indices counting from the end
    (``a.list[-1]``), which both databases apply natively.

    Args:
        column: The JSON column expression (e.g. ``SampleMetadataTable.data``).
        field: Dot-separated path into the JSON object.

    Returns:
        The indexed JSON expression.
    """
    segments = [
        segment if isinstance(segment, int) else _bind_key(segment)
        for segment in _parse_field_path(field)
    ]
    return cast(ColumnElement[Any], functools.reduce(operator.getitem, segments, column))


def json_extract_as_text(column: Any, field: str) -> ColumnElement[str]:
    """Index into a JSON column by field path and read the value as text.

    Text is what comparisons and ``ORDER BY`` need, and it is undecorated on both
    databases.

    Args:
        column: The JSON column expression.
        field: Dot-separated path into the JSON object, as in :func:`json_extract`.

    Returns:
        The extracted value as text.
    """
    return cast(ColumnElement[str], json_extract(column=column, field=field).as_string())


def json_extract_as_float(column: Any, field: str) -> ColumnElement[float]:
    """Index into a JSON column by field path and read the value as a float.

    Casting a non-numeric value fails on PostgreSQL, so guard the call when the
    field's type is not known.

    Args:
        column: The JSON column expression.
        field: Dot-separated path into the JSON object, as in :func:`json_extract`.

    Returns:
        The extracted value as a float.
    """
    return cast(ColumnElement[float], json_extract(column=column, field=field).as_float())


def json_extract_key_as_text(column: Any, key: str) -> ColumnElement[str]:
    """Read one top-level JSON key as text.

    The key is taken literally, so unlike :func:`json_extract_as_text` a dot in it
    stays part of the key rather than stepping into a nested object.

    Args:
        column: The JSON column expression.
        key: The top-level key to read, dots and all.

    Returns:
        The extracted value as text.
    """
    return cast(ColumnElement[str], column[_bind_key(key)].as_string())


class _JsonKeyType(TypeDecorator[str]):
    """Bind one object key so that each database reads it as a key and nothing else.

    DuckDB's ``->`` is ``json_extract``, which reads a leading ``$`` as JSONPath and a
    leading ``/`` as a JSON Pointer. A key such as ``$.temp`` would therefore address
    another part of the document, and ``$x`` would raise. Sending a one-segment JSON
    Pointer removes the ambiguity, because a pointer states where each segment ends.

    PostgreSQL's ``->`` takes a key and nothing else, so the key passes through.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect: Dialect) -> str | None:
        """Convert a DuckDB key to a JSON Pointer and leave a PostgreSQL key raw.

        Args:
            value: The key to bind, or None.
            dialect: The dialect the statement compiles for.

        Returns:
            The value to send to the database.
        """
        if value is None or dialect.name != _DUCKDB_DIALECT:
            return value
        escaped = value.replace("~", "~0").replace("/", "~1")
        return f"/{escaped}"


def _bind_key(key: str) -> ColumnElement[str]:
    """Return the key as a bound parameter that each database reads literally.

    Args:
        key: One object key, taken literally.

    Returns:
        The bound key.
    """
    return sqlalchemy.literal(key, type_=_JsonKeyType())


def _parse_field_path(field: str) -> list[str | int]:
    """Split a field path into key and array-index segments.

    ``"a.list[0]"`` becomes ``["a", "list", 0]``. A bracket group that does not hold an
    index becomes a literal key segment of its own: ``"weird[key]"`` becomes
    ``["weird", "[key]"]``, so it cannot reach SQL as an index. Indices outside the
    32-bit range PostgreSQL subscripts accept are literal keys for the same reason.

    Args:
        field: Dot-separated path into a JSON object.

    Returns:
        The segments, in path order, with array indices as integers.
    """
    segments: list[str | int] = []
    # Split on '.' but keep bracket notation (e.g. "nested_list[0]" -> "nested_list", "[0]")
    for part in field.replace("[", ".[").split("."):
        index_match = _ARRAY_INDEX_PATTERN.match(part)
        if index_match is None:
            segments.append(part)
            continue
        index = int(index_match.group(1))
        segments.append(index if _INT32_MIN <= index <= _INT32_MAX else part)
    return segments
